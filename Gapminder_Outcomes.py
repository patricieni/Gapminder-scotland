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

df_outcomes = df.loc[df.DOMAIN=='Outcomes']

# Make smaller groups and keep only the ones of interest
df_outcomes['GROUP'] = df_outcomes['GEOGRAPHY_NAME'].map(lambda x: x.rsplit(' - ')[0])
df_outcomes['GEOGRAPHYID'] = df_outcomes['GEOGRAPHYID'].astype('str')

## Let's pick only certain areas of Scotland
urban_area = ['Aberdeen City', 'East Lothian', 'Edinburgh, City of','Lothian','West Lothian','Fife','Glasgow City']
df_outcomes_temp = df_outcomes.loc[df_outcomes['GROUP'].isin(urban_area)]


df_outcomes_regions = df_outcomes_temp.copy()
df_outcomes_regions = df_outcomes_regions[['GEOGRAPHYID','GROUP','GEOGRAPHY_NAME']]
df_outcomes_regions.set_index('GEOGRAPHYID',inplace=True)
df_outcomes_regions.head(2)

# Keep only SII and 65+ SII for now and the emergency hospitalization
# Notice change of dataframe throughout to deal only with a portion of the locations
df_rii = df_outcomes_temp[df_outcomes_temp.INDICATOR_DESCRIPTION=='Relative Index of Inequality for patients with emergency hospitalisations']
df_sii = df_outcomes_temp[df_outcomes_temp.INDICATOR_DESCRIPTION=='Slope Index of Inequality for patients with emergency hospitalisations']
df_patients = df_outcomes_temp[df_outcomes_temp.INDICATOR_DESCRIPTION=='Patients with emergency hospitalisations by SIMD quintile']

## Transform the X and Y variables in the right df format understood by gapminder

#index will be the regions GEOGRAPHYID or GEOGRAPHY_NAME and PMD_PERIOD will be the column
# sii values = df_sii.INDICATOR_VALUE
# rii values = df_rii.Indicator_value
sii = df_sii.copy()
sii = sii.pivot(index='GEOGRAPHYID', columns='PMD_PERIOD', values='INDICATOR_VALUE')

rii = df_rii.copy()
rii = rii.pivot(index='GEOGRAPHYID', columns='PMD_PERIOD', values='INDICATOR_VALUE')
rii = rii * 10000000

population = df_patients.copy()
population = population.pivot('GEOGRAPHYID', columns='PMD_PERIOD', values='INDICATOR_VALUE')
#population = population

# gapminder.population # size --> population
# gapminder.fertility # X --> sii 
# gapminder.life_expectancy # Y --> rii
panel = pd.Panel({'SII': sii,
                  'Population': population,
                  'RII': rii})

final = panel.to_frame().reset_index().rename(columns={'minor':'PMD_PERIOD'})

# Apparently there's some values in the GeO ID that are NAN - should remove these before any processing
df_final = final.merge(df_outcomes_regions.drop_duplicates().reset_index(),on='GEOGRAPHYID',how='left')

# Just to be safe i don't get stupid errors
df_final = df_final.dropna()
df_final['GEOGRAPHYID'] = df_final['GEOGRAPHYID'].astype('str')
df_final['GROUP'] = df_final['GROUP'].astype('str')
df_final['GEOGRAPHY_NAME'] = df_final['GEOGRAPHY_NAME'].astype('str')
df_final.PMD_PERIOD = df_final.PMD_PERIOD.astype('f')
df_final.RII = df_final.RII.astype('f')
df_final.SII = df_final.SII.astype('f')
df_final.Population = df_final.Population.astype('f')

ds = hv.Dataset(df_final)

# Apply dimension labels and ranges
# Can invert the axes once it's working
kdims = ['Population', 'SII']
vdims = ['GEOGRAPHY_NAME', 'RII', 'GROUP']
dimensions = {
    'SII' : dict(label='SII (Slope Inequality Index)', range=(3000, 10000)),
    'Population': dict(label='Number of emergencies <65 (Population)', range=(4000, 12500)),
    'RII': ('rii', 'RII')
}

# Create Points plotting fertility vs life expectancy indexed by Year
gapminder_ds = ds.redim(**dimensions).to(hv.Points, kdims, vdims, 'PMD_PERIOD')

# Define annotations
text = gapminder_ds.clone({yr: hv.Text(1.2, 25, str(int(yr)), fontsize=30)
                           for yr in gapminder_ds.keys()})

# Define options
opts = {'plot': dict(width=1000, height=600,tools=['hover'], size_index='RII',
                         color_index='GROUP', size_fn=np.sqrt, title_format="{label}"),
       'style': dict(cmap='Set1', size=0.3, line_color='black', alpha=0.6)}
text_opts = {'style': dict(text_font_size='52pt', text_color='lightgray')}

# Combine Points and Text
hvgapminder = (gapminder_ds({'Points': opts}) * text({'Text': text_opts})).relabel('Gapminder Scotland')

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
