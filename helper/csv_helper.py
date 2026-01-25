#!/usr/bin/python

__author__ = "Alan Saunders"
__purpose__ = "Allows you to modify the RingCentral Global Shared Address book export. The script will automatically format the output csv to match what is expected by RingCentral. "
__version__ = "0.1"
__github__ = "https://github.com/Ripped-Kanga/RingCentral-CSV-Editor\n"

# Import Libraries
import os
import csv
import re
from datetime import datetime
from pathlib import Path
from typing import Iterable



class RingCentralCSV:
	'''
	Helper class to handle the RingCentral address book file.
	'''
	def __init__(self, csv_in=None, csv_path_out="results"):
		self.csv_in = csv_in
		self.csv_path_out = csv_path_out

		if os.path.exists(self.csv_path_out):
			pass
		else:
			print(f"/{self.csv_path_out} does not exist, creating...")
			os.makedirs(csv_path_out, exist_ok=True)


	def checker(self, csv_in_path: str, required_headers: Iterable[str] = ("First Name", "Surname")) -> list[dict]:
		'''
		Check the file until the real header row is found, then parse into list dict. 
		Returns list dict, sets self.fieldnames.
		
		required_headers: headers that MUST appear in the header row
		'''
		path = Path(csv_in_path).expanduser()

		if not path.exists():
			raise FileNotFoundError(f"CSV not found: {path}")

		required = {h.strip() for h in required_headers}

		with path.open("r", newline="", encoding="utf-8-sig") as f:
			start = f.read(2048)
			if not start.strip():
				self.fieldnames = []
				raise ValueError("CSV is empty (no headers).")

			f.seek(0)

			while True:
				pos = f.tell()
				line = f.readline()

				if line == "":
					raise ValueError(f"Could not find header row containing {sorted(required)} in file: {path}")

				row = next(csv.reader([line]))
				row_set = {cell.strip().lstrip("\ufeff") for cell in row}

				if required.issubset(row_set):
					f.seek(pos)
					reader = csv.DictReader(f)
					self.fieldnames = reader.fieldnames or []
					return list(reader)


	def appender(self, csv_data):
		print ("Enter your new values")
		allowed = {"y", "n"}

		while True:
			new_entry = {k: "" for k in self.fieldnames}

			# collect one row
			for key in self.fieldnames:
				while True:
					raw_text = input(f"{key}: ").strip()
					try:
						new_entry[key] = self.field_formatter(key, raw_text)
						break
					except ValueError as e:
						print(f"Invalid entry for '{key}': {e}")
						print("Try again, or press Enter to leave blank.")

			csv_data.append(new_entry)


			# ask to add another
			while True:
				add_more = input("Do you want to add more? (Y/N): ").strip().lower()
				if add_more in allowed:
					break
				print("Please only enter Y or N.")

			if add_more == "n":
				break
		filename = input("What will the new csv filename be? ")
		path = filename+".csv"
		self.writer(path, self.fieldnames, csv_data)


	def writer(self, fieldnames: list[str], csv_data: list[dict]) -> Path:
		'''
		Accepts incoming csv data after appended data is added to the new list. 
		Writes a new csv file with date stamp.
		'''
		
		file_date = datetime.now().strftime("%Y%m%d-%H%M")

		out_dir = Path(self.csv_path_out).expanduser()
		out_dir.mkdir(parents=True, exist_ok=True)

		out_path = out_dir / f"AddressBook-{file_date}.csv"

		with out_path.open("w", newline="", encoding="utf-8") as f:
			writer = csv.DictWriter(f, fieldnames=fieldnames, extrasaction="ignore")
			writer.writeheader()
			writer.writerows(csv_data)

		return out_path

	@staticmethod
	def field_formatter(fieldnames, value: str) -> str:

		field = fieldnames.strip().casefold()
		raw_value = value.strip()
		"""
		Automatically normalises entries based on field header. 
		
		Names:
		  Strings only, no numbers. 

		Email:
		  Email only

		Job Title/Company Name:
		  Strings only, no numbers.

		Mobiles:
		  04XXXXXXXX      -> +614XXXXXXXX
		  614XXXXXXXX     -> +614XXXXXXXX
		  +614XXXXXXXX    -> +614XXXXXXXX

		Landlines:
		  0[2378]XXXXXXXX -> +61[2378]XXXXXXXX
		  +61[2378]XXXXXXXX stays as-is

		Service numbers:
		  13XXXX          -> +6113XXXX
		  1300XXXXXX      -> +611300XXXXXX
		  1800XXXXXX      -> +611800XXXXXX
		"""

		# If nothing is entered just return nothing.
		if raw_value == "":
			return ""

		# --- Names ---
		if field in {"first name", "surname"}:
			if not re.fullmatch(r"[A-Za-z]+(?:[ '\-][A-Za-z]+)*", raw_value):
				raise ValueError("Names must contain letters only (spaces, hyphens, apostrophes allowed)")
			return raw_value.title()

		# --- Job title / Company ---
		if field in {"job title", "company"}:
			if not re.fullmatch(r"[A-Za-z]+(?:[ '\-][A-Za-z]+)*", raw_value):
				raise ValueError("Names must contain letters only (spaces, hyphens, apostrophes allowed)")
			return raw_value.title()

		# --- Email --- 
		if field == "email":
			email = raw_value.lower()
			if not re.fullmatch(r"[^@\s]+@[^@\s]+\.[^@\s]+", email):
				raise ValueError("Email doesn't look valid (expected name@domain.tld)")
			return email

		# --- Phone numbers (AU) ---
		if field in {"home number", "business number", "mobile number", "company main number"}:
			number_cleaned = raw_value
			number_cleaned = re.sub(r"[^\d+]", "", number_cleaned)

		# If starts with +, validate then return
		if number_cleaned.startswith("+"):
			# Mobile +614XXXXXXXX
			if re.fullmatch(r"\+614\d{8}", number_cleaned):
				return number_cleaned
			# Landline +61[2378]XXXXXXXX
			if re.fullmatch(r"\+61[2378]\d{8}", number_cleaned):
				return number_cleaned
			# Service +6113xxxx or +611300xxxxxx or +611800xxxxxx
			if re.fullmatch(r"\+6113\d{4}", number_cleaned) or re.fullmatch(r"\+611(300|800)\d{6}", number_cleaned):
				return number_cleaned
			raise ValueError("Expected Australian number in E.164 format (e.g. +614..., +612..., +611300...)")

		# Digits only
		number_cleaned = re.sub(r"\D", "", number_cleaned)

		# Mobile
		if re.fullmatch(r"04\d{8}", number_cleaned):
			return "+61" + number_cleaned[1:]
		if re.fullmatch(r"614\d{8}", number_cleaned):
			return "+" + number_cleaned

		# Landline: 02/03/07/08 + 8 digits
		if re.fullmatch(r"0[2378]\d{8}", number_cleaned):
			return "+61" + number_cleaned[1:]
		if re.fullmatch(r"61[2378]\d{8}", number_cleaned):
			return "+" + number_cleaned

		# Service numbers
		if re.fullmatch(r"13\d{4}", number_cleaned):
			return "+61" + number_cleaned
		if re.fullmatch(r"1300\d{6}", number_cleaned) or re.fullmatch(r"1800\d{6}", number_cleaned):
			return "+61" + number_cleaned
		if re.fullmatch(r"6113\d{4}", number_cleaned) or re.fullmatch(r"61(300|800)\d{6}", number_cleaned):
			return "+" + number_cleaned

		raise ValueError("Not a valid AU phone number (mobile, landline(include area code), or 13/1300/1800)")

		# --- Source / External ID ---
		if field in {"source", "external id"}:
			return raw_value