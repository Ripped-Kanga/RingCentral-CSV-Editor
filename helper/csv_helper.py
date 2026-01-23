#!/usr/bin/python

__author__ = "Alan Saunders"
__purpose__ = "Allows you to modify the RingCentral Global Shared Address book export. The script will automatically format the output csv to match what is expected by RingCentral. "
__version__ = "0.1"
__github__ = "https://github.com/Ripped-Kanga/RingCentral-CSV-Editor\n"

# Import Libraries
import os
import csv
from datetime import datetime
import pprint


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


	'''
	Checks the incoming csv file to see if it has RingCentral junk comment data. If it does
	strip the junk data out and write a new dict starting from row 24.
	If it doesn't, ingest the csv, checking that the headers are correct.
	'''
	def checker(self, csv_in_path):
		with open(csv_in_path, newline="", encoding="utf-8") as f:
			first_line = f.readline()
			check_junk = (first_line or "").strip().lstrip('"')

		with open(csv_in_path, newline="", encoding="utf-8") as csvfile:

			if check_junk.startswith("Please follow the"):
				header_row = 24
				# Skip lines 1..23 as they contain junk data
				for _ in range(header_row - 1):
					next(csvfile, None)

				reader = csv.DictReader(csvfile)  # line 24 becomes the header row
				cleaned_rows = list(reader)

				pprint.pprint (cleaned_rows, sort_dicts=False)
				print ("Data was dirty")

			elif check_junk.startswith("First Name,Surname,"):
				print("File is clean, writing csv data to dictionary...")
				reader = csv.DictReader(csvfile, delimiter=",")
				data_ingest = list(reader)
				pprint.pprint(data_ingest, sort_dicts=False)

				print ("Data was clean")

			else:
				print("Error in csv_in condition logic")
				exit()


	def csv_writer(self, csv_out_path):
		with open('eggs.csv', 'w', newline='') as csvfile:
			new_address_book = csv.writer(csvfile, delimiter=',')