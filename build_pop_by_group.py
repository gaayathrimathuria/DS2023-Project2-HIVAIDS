"""One-time script: shrink the 117 MB California population file into pop_by_group.csv.

The notebook only needs population totals per Year/Category/Group, so this does the heavy
work once and saves the small result. Run it again only if the raw population file changes:

    python build_pop_by_group.py

Then upload pop_by_group.csv to Box (or keep it in the repo) and load it in Project2.ipynb.
"""
import os
import pandas as pd

POP_DATA_URL = 'https://virginia.box.com/shared/static/k8m08mo65opxkqtzr4cy3btbyk8dkvmt.csv'
OUTPUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'pop_by_group.csv')

# reading only the needed columns, and storing repeated text as categories, keeps memory low
pop = pd.read_csv(POP_DATA_URL,
                  usecols=['county_lhj', 'year', 'sex', 'age', 'race_eth', 'population',
                           'county_indicator', 'lhj_indicator'],
                  dtype={'county_lhj': 'category', 'sex': 'category', 'race_eth': 'category'})
pop = pop[pop.year.between(2010, 2023)]

# the file counts counties and local health jurisdictions separately, so keeping only county rows
# gives a complete state total without counting Berkeley, Long Beach and Pasadena twice
pop_state = pop[pop.county_indicator == 1].copy()

# relabeling so the population groups match the Group labels in the HIV data
race_labels = {'AI/AN': 'American Indian/Alaska Native', 'Asian': 'Asian', 'Black': 'Black/African American',
               'Latino': 'Latine', 'Multi-Race': 'Multiple races',
               'NH/PI': 'Native Hawaiian/Pacific Islander', 'White': 'White'}
# same bins as the HIV data, which are inclusive of the lower and upper bounds
age_bins = [-1, 11, 14, 17, 19, 24, 29, 34, 39, 44, 49, 54, 59, 64, 74, 200]
age_labels = ['0 to 11', '12 to 14', '15 to 17', '18 to 19', '20 to 24', '25 to 29', '30 to 34', '35 to 39',
              '40 to 44', '45 to 49', '50 to 54', '55 to 59', '60 to 64', '65 to 74', '>= 75']

pop_state['Race/Ethnicity'] = pop_state.race_eth.astype(str).map(race_labels)
pop_state['Age'] = pd.cut(pop_state.age, bins=age_bins, labels=age_labels).astype(str)
pop_state['Sex at Birth'] = pop_state.sex.astype(str)
pop_state['County'] = pop_state.county_lhj.astype(str)

# summing each category separately (instead of melting first) avoids building a 4x longer table
pieces = []
for category in ['Age', 'Race/Ethnicity', 'Sex at Birth', 'County']:
    totals = pop_state.groupby(['year', category], observed=True).population.sum().reset_index()
    pieces.append(totals.rename(columns={category: 'Group'}).assign(Category=category))

# the three cities are their own health jurisdictions, so they come from the lhj rows instead
pop_cities = pop[(pop.lhj_indicator == 1) & (pop.county_lhj.isin(['Berkeley', 'Long Beach', 'Pasadena']))]
pop_cities = (pop_cities.assign(Group=pop_cities.county_lhj.astype(str))
              .groupby(['year', 'Group']).population.sum().reset_index().assign(Category='City'))
pieces.append(pop_cities)

pop_by_group = (pd.concat(pieces)
                .rename(columns={'year': 'Year', 'population': 'Population'})
                [['Year', 'Category', 'Group', 'Population']]
                .sort_values(['Year', 'Category', 'Group'])
                .reset_index(drop=True))

pop_by_group.to_csv(OUTPUT, index=False)
print(f'Saved {len(pop_by_group):,} rows to {OUTPUT}')
