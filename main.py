#!/usr/bin/python

__author__ = "Alan Saunders"
__purpose__ = ""
__version__ = "0.1"
__github__ = "https://github.com/Ripped-Kanga/RingCentral-CSV-Editor\n"
__disclaimer__ = ""


# Import Libraries
import sys
import os
import pprint
from helper.csv_helper import RingCentralCSV

def main():
	# Always open csv file first before asking the user what they want to do.
	rc_csv = RingCentralCSV()
	try:
		csv_name = input("Specify the csv file name: ")
		csv_data = rc_csv.checker(csv_name)
	except FileNotFoundError as e:
		print(e)
		print("The filename entered is incorrect! Please check the name and try again.\n")
		main()

	row_count  = len(csv_data)
	print(f"There is currently {row_count} rows in the csv file.")
	allowed = {"New", "Read", "Append", "Delete"}

	while True:
		user_action = input("What do you want to do? (New File, Read, Append, Delete): ")
		user_selection = user_action.title()
		if user_selection in allowed:
			break
		print (f"Please enter {allowed}")

	if user_selection == "New":
		pass

	if user_selection == "Read":
		pass

	if user_selection == "Append":
		rc_csv.appender(csv_data)

	if user_selection == "Delete":
		pass


# Start Execution
if __name__ == "__main__":
	# Start main() and listen for keyboard interrupts
	try:
		main()
	except KeyboardInterrupt:
		print('\nInterrupted by keyboard CTRL + C, exiting...\n')
		try:
			sys.exit(130)
		except SystemExit:
			os._exit(130)