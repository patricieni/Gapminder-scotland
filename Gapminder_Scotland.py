import pandas as pd
import numpy as np
import holoviews as hv

from bokeh.io import curdoc
from bokeh.layouts import layout
from bokeh.models import Slider, Button
from bokeh.sampledata import gapminder
from holoviews.plotting.bokeh import BokehRenderer

renderer = hv.renderer('bokeh')

df = pd.read_csv("data/Deprivation_20180313_raw_data.csv")
df_health = df.loc[df.DOMAIN == "Health inequalities and physical activity"]

# Make smaller groups and keep only the ones of interest
df_health['GROUP'] = df_health['GEOGRAPHY_NAME'].map(lambda x: x.rsplit(' - ')[0])
df_health['GEOGRAPHYID'] =df_health['GEOGRAPHYID'].astype(str)

urban_area = ['Aberdeen City', 'East Lothian', 'Edinburgh, City of','Lothian','West Lothian','Fife','Glasgow City']
df_health_temp = df_health.loc[df_health['GROUP'].isin(urban_area)]


df_health_regions = df_health_temp.copy()
df_health_regions = df_health_regions[['GEOGRAPHYID','GROUP','GEOGRAPHY_NAME']]
df_health_regions.set_index('GEOGRAPHYID',inplace=True)
#df_health_regions.head(2)

female_health = df_health_temp[df_health_temp.INDICATOR_DESCRIPTION=='Female life expectancyÂ\xa0by SIMD quintileÂ\xa0']
male_health = df_health_temp[df_health_temp.INDICATOR_DESCRIPTION=='Male life expectancy by SIMD quintile']
mortality_health = df_health_temp[df_health_temp.INDICATOR_DESCRIPTION=='All-cause mortality among the 15-44 year olds by SIMD quintile']

fh = female_health.copy()
fh = fh.pivot(index='GEOGRAPHYID', columns='PMD_PERIOD', values='INDICATOR_VALUE')

mh = male_health.copy()
mh = mh.pivot(index='GEOGRAPHYID', columns='PMD_PERIOD', values='INDICATOR_VALUE')

population = mortality_health.copy()
population = population.pivot(index='GEOGRAPHYID', columns='PMD_PERIOD', values='INDICATOR_VALUE')
population = population

# gapminder.population # size --> population
# gapminder.fertility # X --> sii 
# gapminder.life_expectancy # Y --> rii
panel = pd.Panel({'Female_Health': fh,
                  'Population': population,
                  'Male_Health': mh})

final = panel.to_frame().reset_index().rename(columns={'minor':'PMD_PERIOD'})

# Apparently there's some values in the GeO ID that are NAN - should remove these before any processing
df_final = final.merge(df_health_regions.drop_duplicates().reset_index(),on='GEOGRAPHYID',how='left')

# Just to be safe i don't get stupid errors
df_final = df_final.dropna()
df_final['GEOGRAPHYID'] = df_final['GEOGRAPHYID'].astype('str')
df_final['GROUP'] = df_final['GROUP'].astype('str')
df_final['GEOGRAPHY_NAME'] = df_final['GEOGRAPHY_NAME'].astype('str')
df_final.PMD_PERIOD = df_final.PMD_PERIOD.astype('f')
df_final.Female_Health = df_final.Female_Health.astype('f')
df_final.Male_Health = df_final.Male_Health.astype('f')
df_final.Population = df_final.Population.astype('f')
df_final.Population = df_final.Population * 100000
ds = hv.Dataset(df_final)

# Apply dimension labels and ranges
# Can invert the axes once it's working
kdims = ['Female_Health', 'Male_Health']
vdims = ['GEOGRAPHY_NAME', 'Population', 'GROUP']
dimensions = {
    'Male_Health' : dict(label='Male_Health (Life Expectancy)', range=(40, 100)),
    'Female_Health': dict(label='Female_Health (Life Expectancy))', range=(40, 100)),
    'Population': ('population', 'Population')
}

# Create Points plotting fertility vs life expectancy indexed by Year
gapminder_ds = ds.redim(**dimensions).to(hv.Points, kdims, vdims, 'PMD_PERIOD')

# Define annotations
text = gapminder_ds.clone({yr: hv.Text(1.2, 25, str(int(yr)), fontsize=30)
                           for yr in gapminder_ds.keys()})

# Define options
opts = {'plot': dict(width=1000, height=600,tools=['hover'], size_index='Population',
                         color_index='GROUP', size_fn=np.sqrt, title_format="{label}"),
       'style': dict(cmap='Set1', size=0.3, line_color='black', alpha=0.6)}
text_opts = {'style': dict(text_font_size='52pt', text_color='lightgray')}

# Combine Points and Text
hvgapminder = (gapminder_ds({'Points': opts}) * text({'Text': text_opts})).relabel('Health in Urban Scotland')

# Define custom widgets
def animate_update():
    year = slider.value + 1
    if year > end:
        year = start
    slider.value = year

# Update the holoviews plot by calling update with the new year.
def slider_update(attrname, old, new):
    hvplot.update((new,))

def animate():
    if button.label == '► Play':
        button.label = '❚❚ Pause'
        doc.add_periodic_callback(animate_update, 200)
    else:
        button.label = '► Play'
        doc.remove_periodic_callback(animate_update)

start, end = ds.range('PMD_PERIOD')
slider = Slider(start=start, end=end, value=start, step=1, title="PMD_PERIOD")
slider.on_change('value', slider_update)
        
button = Button(label='► Play', width=60)
button.on_click(animate)

# Get HoloViews plot and attach document
doc = curdoc()
hvplot = BokehRenderer.get_plot(hvgapminder, doc)

# Make a bokeh layout and add it as the Document root
plot = layout([[hvplot.state], [slider, button]], sizing_mode='fixed')
doc.add_root(plot)
