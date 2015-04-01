
"""
title: Crop choice optimizition 
author: michael.james.asher@gmail.com
date: January 2015

To maximise revenue subject to water and land area constraints, we use scipy.optimize, scipy.linprog and linear programming optimizition library PULP, eg. https://pythonhosted.org/PuLP/index.html	

"""


from scipy.optimize import minimize
from scipy.optimize import linprog
import numpy as np
import os

# maximise revenue subject to water and land area constraints
def scipy_linprog_find_optimal_crops(crops, farm_area, water_licence):

	# objective function
	c = [crop['cost ($/ha)'] - np.sum(crop["yield (units/ha)"] * crop["price ($/unit)"]) for crop in crops]
	# contstraints
	A = [
		# water use must be less than licence
		[crop["water use (ML/ha)"] for crop in crops]
		]
	b = [water_licence]
	# total area farmed each season must be less than farm area for each type of irrgation
	for season in ["Summer", "Winter"]:
		for area_type in ["flood_irrigation", "spray_irrigation", "drip_irrigation"]:
			A.append(map(int,[crop["season"] == season and crop["area type"] == area_type for crop in crops]))
			b.append(farm_area[area_type])
		# dryland crops may grow on any type
		A.append(map(int,[crop["season"]==season for crop in crops]))
		b.append(farm_area["flood_irrigation"]+farm_area["drip_irrigation"]+farm_area["spray_irrigation"]+farm_area["dryland"])


	bounds = ((0,None),)*len(crops)

	res = linprog(c, A_ub=A, b_ub=b, bounds=bounds, options={"disp": True})
	return res


def read_crops_csv(file_name):
	import csv
	import json
	crops = []
	with open(file_name) as csvfile:
	    reader = csv.DictReader(csvfile)
	    for row in reader:
	    	if row['valid'] == 'TRUE':
	    		try: 
	    			row['yield (units/ha)'] = np.array(json.loads(row['yield (units/ha)']))
	    			row['price ($/unit)'] = np.array(json.loads(row['price ($/unit)']))
	    			row['cost ($/ha)'] = float(row['cost ($/ha)'])
	    			row["water use (ML/ha)"] = float(row["water use (ML/ha)"])
	    			crops.append(row)
	    		except: 
	    			print "invalid crop", row

	    		# row['water use (ML/ha)'] = json.loads(row['water use (ML/ha)'])
	    		# row['cost ($/ha)'] = json.loads(row['cost ($/ha)'])
	return crops

# print results
def print_results(res, crops):
	print "Crops grown"
	print "----------------------------------------"
	for i, x_i in enumerate(res.x):
		if x_i > 1e-3:
			print crops[i]["name"], "-", x_i, "ha"
	print "----------------------------------------"

	for season in ["Summer", "Winter"]:
		for area_type in ["flood_irrigation", "spray_irrigation", "drip_irrigation"]:
			print season, area_type, 'area', sum([res.x[i] for i,crop in enumerate(crops) if crop["season"] == season and crop["area type"] == area_type  ]), "ha"
	print "total summer area", sum([res.x[i] for i,crop in enumerate(crops) if crop["season"] == "Summer" ]), "ha"
	print "total winter area", sum([res.x[i] for i,crop in enumerate(crops) if crop["season"] == "Winter" ]), "ha"
	print "water", sum([res.x[i] * crop["water use (ML/ha)"] for i,crop in enumerate(crops)]), "ML"
	print "farm revenue", "$", sum([res.x[i] * (np.sum(crop["yield (units/ha)"] * crop["price ($/unit)"]) - crop['cost ($/ha)']) for i, crop in enumerate(crops)])/1e6, "M"

	print "========================================"

	# print res

def maximum_profit(crops, farm_area, total_water_licence):

	res = scipy_linprog_find_optimal_crops(crops, farm_area, total_water_licence)
	return sum([res.x[i] * (np.sum(crop["yield (units/ha)"] * crop["price ($/unit)"]) - crop['cost ($/ha)']) for i, crop in enumerate(crops)])


farm_dir = os.path.dirname(__file__)+'/'

def load_crops():
	# http://www.dpi.nsw.gov.au/agriculture/farm-business/budgets/summer-crops
	# http://www.dpi.nsw.gov.au/agriculture/farm-business/budgets/winter-crops
	dpi_budget_crops = read_crops_csv(farm_dir+'dpi_budget_crops.csv') 
	# powell2011representative
	powell_crops = read_crops_csv(farm_dir+'powell_crops.csv') 
	# SEMI-IRRIGATED COTTON: MOREE LIMITED WATER EXPERIMENT
	other_crops	= [{
			'name': 'SEMI-IRRIGATED COTTON',
			'yield (units/ha)': 7,
			'season': 'Summer',
			'water use (ML/ha)': 4.5,
			'source': 'fabricated',
			'cost ($/ha)': 2000,
			'price ($/unit)': 380,
			'area type': 'flood_irrigation'
			}]

	all_crops = dpi_budget_crops + powell_crops + other_crops

	return all_crops


if __name__ == '__main__':

	# demo run
	water_licence = {"sw_unregulated": 1413, "gw": 2200}
	total_water_licence = water_licence['sw_unregulated']+water_licence['gw']
	farm_area = {"flood_irrigation": 782, "spray_irrigation": 0, "drip_irrigation": 0, "dryland": 180}

	# http://www.dpi.nsw.gov.au/agriculture/farm-business/budgets/summer-crops
	# http://www.dpi.nsw.gov.au/agriculture/farm-business/budgets/winter-crops
	dpi_budget_crops = read_crops_csv('dpi_budget_crops.csv') 
	# powell2011representative
	powell_crops = read_crops_csv('powell_crops.csv') 
	# SEMI-IRRIGATED COTTON: MOREE LIMITED WATER EXPERIMENT
	other_crops	= [{
			'name': 'SEMI-IRRIGATED COTTON',
			'yield (units/ha)': 7,
			'season': 'Summer',
			'water use (ML/ha)': 4.5,
			'source': 'fabricated',
			'cost ($/ha)': 2000,
			'price ($/unit)': 380,
			'area type': 'flood_irrigation'
			}]

	demo_crops = dpi_budget_crops + powell_crops + other_crops



	res_linprog = scipy_linprog_find_optimal_crops(demo_crops, farm_area, total_water_licence)
	print_results(res_linprog, demo_crops)

	print maximum_profit(demo_crops, farm_area, total_water_licence)





"""
BIBLIOGRAPHY

@book{powell2011representative,
  title={A representative irrigated farming system in the Lower Namoi Valley of NSW: An economic analysis},
  author={Powell, Janine and Scott, Fiona and Wales, New South},
  year={2011},
  publisher={Industry \& Investment NSW},
  url={http://www.dpi.nsw.gov.au/research/economics-research/reports/err46
}
}

@article{zwart2004review,
  title={Review of measured crop water productivity values for irrigated wheat, rice, cotton and maize},
  author={Zwart, Sander J and Bastiaanssen, Wim GM},
  journal={Agricultural Water Management},
  volume={69},
  number={2},
  pages={115--133},
  year={2004},
  publisher={Elsevier}
}



"""
