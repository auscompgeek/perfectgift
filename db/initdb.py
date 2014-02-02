#!/usr/bin/env python3

import re
import os
import sqlite3
import random
import argparse

from password import hash_password, generate_salt

def getpath(fname):
	dirname = os.path.dirname(__file__)
	return os.path.join(dirname, fname)

def generate_fake_users(conn):
	names = []
	with open(getpath("random_names.txt")) as f:
		names = [name.strip() for name in f]

	for i in range(len(names)):
		fname, lname = random.sample(names, 2)
		username = (fname[0] + lname).lower()

		email = "{}{:03}@yoloteamfour.com".format(username, random.randint(0, 100))

		salt = generate_salt()
		password = username[::-1]
		password = hash_password(password, salt)

		dob = "{:04}-{:02}-{:02}".format(random.randint(1970, 2000), random.randint(1, 12), random.randint(1, 28))

		try:
			conn.execute("""INSERT INTO tbl_users (fname, lname, username, email, password, salt, dob) VALUES (?, ?, ?, ?, ?, ?, strftime('%s', ?))""",
					(fname, lname, username, email, password, salt, dob))
		except sqlite3.IntegrityError:
			pass

	conn.commit()

def initdb(dbfile='wishlist.db', fake=True):
	# Clear the file.
	with open(dbfile, "w") as f:
		pass

	conn = sqlite3.connect(dbfile)
	script = ""

	with open(getpath("clean.sql")) as f:
		script += f.read()

	with open(getpath("init.sql")) as f:
		script += f.read()

	conn.executescript(script)
	conn.commit()

	if fake:
		with open(getpath("fake.sql")) as f:
			conn.executescript(f.read())
			conn.commit()

		generate_fake_users(conn)

	conn.close()

if __name__ == "__main__":
	parser = argparse.ArgumentParser(description="Generate the 'perfectgift.com' sqlite database.")
	parser.add_argument('-d', '--dbfile', help="path to database file to be created", type=str, default='wishlist.db')
	parser.add_argument('-f', '--fake', help="generate fake users, wishlists, products and friends", action="store_true")
	args = parser.parse_args()

	initdb(args.dbfile, args.fake)
	#import cProfile
	#print(cProfile.run("initdb()"))
