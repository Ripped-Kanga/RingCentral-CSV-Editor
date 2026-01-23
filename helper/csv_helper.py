#!/usr/bin/python

__author__ = "Alan Saunders"
__purpose__ = "Allows you to modify the RingCentral Global Shared Address book export. "
__version__ = "0.1"
__github__ = "https://github.com/Ripped-Kanga/RingCentral-CSV-Editor\n"
__disclaimer__ = ""


# Import Libraries
import os
import csv
from datetime import datetime


# Helper to ingest the RingCentral Global Shared address book csv file. 
class RingCentralCSV:
	def __init__(self, csv_in=None, csv_path_out="result"):
		self.csv_in = csv_in
		self.csv_path_out = csv_path_out

		if os.path.exists(self.csv_path_out):
			pass
		else:
			print(f"/{self.csv_path_out} does not exist, creating...")
			os.makedirs(csv_path_out, exist_ok=True)

	def _test(self, name):
		date = datetime.now().strftime("%y-%m-%d")
		return (f"{name} - {date}")

	def csv_reader(self, csv_in_path):
		with open(csv_in_path, newline='') as csvfile:
		    address_book = csv.reader(csvfile, delimiter=' ', quotechar='|')
		    for row in address_book:
		        print(', '.join(row))