#!/usr/bin/env python3
# perfectgift: a tornado webapp for creating wish lists between friends
# Copyright (C) 2014, NCSS14 Group 4

# Permission is hereby granted, free of charge, to any person obtaining a copy of
# this software and associated documentation files (the "Software"), to deal in
# the Software without restriction, including without limitation the rights to
# use, copy, modify, merge, publish, distribute, sublicense, and/or sell copies of
# the Software, and to permit persons to whom the Software is furnished to do so,
# subject to the following conditions:

# 1. The above copyright notice and this permission notice shall be included in
#    all copies or substantial portions of the Software.

# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
# SOFTWARE.

import sqlite3

from tornado.log import app_log
from db.password import hash_password, generate_salt

class UserNotFound(Exception):
	pass

class ProductNotFound(Exception):
	pass

class FriendAlreadyAdded(Exception):
	pass

_conn = None

def init(dbfile="wishlist.db"):
	global _conn
	_conn = sqlite3.connect(dbfile)
	_conn.row_factory = sqlite3.Row

class User:
	def __init__(self, user_id, fname, lname, username, email, image=None, dob=None):
		self.user_id = user_id
		self.fname = fname
		self.lname = lname
		self.username = username
		self.email = email

		self.image = image or 'default.gif'
		self.dob = dob or None

	#################
	# CLASS METHODS #
	#################

	@classmethod
	def find(cls, username):
		cur = _conn.execute('''SELECT rowid AS user_id, fname, lname, username, email, image, dob FROM tbl_users WHERE username = ? LIMIT 1''', (username,))
		row = cur.fetchone()

		if not row:
			app_log.warn("user with the username {!r} could not be found".format(username))
			raise UserNotFound('Username {!r} does not exist'.format(username))

		return cls(**row)

	@classmethod
	def find_uid(cls, uid):
		cur = _conn.execute('''SELECT rowid AS user_id, fname, lname, username, email, image, dob FROM tbl_users WHERE rowid = ? LIMIT 1''', (uid,))
		row = cur.fetchone()

		if not row:
			app_log.warn("user with the uid {} could not be found".format(uid))
			raise UserNotFound('Uid {} does not exist'.format(uid))

		return cls(**row)

	@classmethod
	def search(cls, search):
		cur = _conn.execute('''SELECT rowid AS user_id FROM tbl_users WHERE tbl_users MATCH ?''', (search,))
		rows = cur.fetchall()

		return [cls.find_uid(row['user_id']) for row in rows]

	@classmethod
	def create(cls, fname, lname, username, email, password, image=None, dob=None):
		salt = generate_salt()
		password_hash = hash_password(password, salt)

		dob = dob or None
		image = image or 'default.gif'

		_conn.execute('''INSERT INTO tbl_users (fname, lname, username, email, image, password, salt, dob) VALUES (?, ?, ?, ?, ?, ?, ?, ?)''', (fname, lname, username, email, image, password_hash, salt, dob))
		_conn.commit()

		return cls.find(username)

	@classmethod
	def check_password(cls, username, password):
		cur = _conn.execute('''SELECT password, salt FROM tbl_users WHERE username = ? LIMIT 1''', (username,))
		row = cur.fetchone()

		if not row:
			return False

		salt = row['salt']
		password_hash = hash_password(password, salt)

		if password_hash == row['password']:
			return True

		return False

	#######################
	# MODIFY USER METHODS #
	#######################

	def delete(self):
		_conn.execute('''DELETE FROM tbl_users WHERE rowid = ?''', (self.user_id,))
		_conn.commit()

	def save(self):
		self.dob = self.dob or None
		self.image = self.image or 'default.gif'

		_conn.execute('''UPDATE tbl_users SET fname = ?, lname = ?, username = ?, email = ?, image = ?, dob = ? WHERE rowid = ?''', (self.fname, self.lname, self.username, self.email, self.image, self.dob, self.user_id))
		_conn.commit()

	# TODO: Put this in some globals file.
	def get_profile_image(self):
		return '/static/images/profiles/' + self.image

	##########################
	# QUERY WISHLIST METHODS #
	##########################

	def get_wishlists(self):
		cur = _conn.execute('''SELECT wish_id, list_name FROM tbl_wish_list WHERE user_id = ?''', (self.user_id,))
		rows = cur.fetchall()

		wishlists = []

		for row in rows:
			wishlist = Wishlist(user=self, **row)
			wishlists.append(wishlist)

		return wishlists

	#########################
	# MODIFY FRIEND METHODS #
	#########################

	def add_friend(self, friend):
		if not self.check_friend(friend):
			_conn.execute('''INSERT INTO tbl_friends (f_user_id, friend_id) VALUES (?, ?)''', (self.user_id, friend.user_id))
			_conn.commit()
		else:
			app_log.warn("{!r} is already a friend of {!r}".format(friend.username, self.username))
			raise FriendAlreadyAdded('{} has already been added as a friend of {}'.format(friend.username, self.username))

	def delete_friend(self, friend):
		_conn.execute('''DELETE FROM tbl_friends WHERE (f_user_id = ? AND friend_id = ?) OR (f_user_id = ? AND friend_id = ?)''', (self.user_id, friend.user_id, friend.user_id, self.user_id))
		_conn.commit()

	########################
	# QUERY FRIEND METHODS #
	########################

	def check_friend(self, friend):
		cur = _conn.execute('''SELECT COUNT(*) FROM tbl_friends WHERE (f_user_id = ? AND friend_id = ?) OR (f_user_id = ? AND friend_id = ?)''', (self.user_id, friend.user_id, friend.user_id, self.user_id))
		count = cur.fetchone()[0]

		return count == 2

	def check_pending_friend(self, friend):
		cur = _conn.execute('''SELECT COUNT(*) FROM tbl_friends WHERE f_user_id = ? AND friend_id = ?''', (self.user_id, friend.user_id))
		count = cur.fetchone()[0]

		return count > 0

	def find_friends(self):
		cur = _conn.execute('''SELECT f_user_id FROM tbl_friends WHERE friend_id = ? INTERSECT SELECT friend_id FROM tbl_friends WHERE f_user_id = ?''', (self.user_id, self.user_id))
		rows = cur.fetchall()

		return [User.find_uid(row['f_user_id']) for row in rows]


class Product:
	def __init__(self, product_id, name, image, link, description, price, checked=0):
		self.product_id = product_id
		self.name = name
		self.image = image or '/static/images/gift_box.png'
		self.link = link
		self.description = description
		self.price = price
		self.checked = checked or 0

	#################
	# CLASS METHODS #
	#################

	@classmethod
	def find(cls, product_id):
		cur = _conn.execute('''SELECT p.rowid AS product_id, p.name, p.image, p.link, p.description, p.price, i.checked FROM tbl_products AS p LEFT JOIN tbl_list_item AS i ON p.rowid = i.product_id WHERE p.rowid = ? LIMIT 1''', (product_id,))
		row = cur.fetchone()

		if not row:
			app_log.warn("product {} could not be found".format(product_id))
			raise ProductNotFound('{} does not exist'.format(product_id))

		return cls(*row)

	@classmethod
	def search(cls, search):
		cur = _conn.execute('''SELECT rowid AS product_id FROM tbl_products WHERE tbl_products MATCH ?''', (search,))
		rows = cur.fetchall()

		return [cls.find(row['product_id']) for row in rows]

	@classmethod
	def create(cls, name, image, link, description, price):
		_conn.execute('''INSERT INTO tbl_products (name, image, link, description, price) VALUES (?, ?, ?, ?, ?)''', (name, image, link, description, price))
		_conn.commit()

		cur = _conn.execute("SELECT last_insert_rowid()")
		product_id = cur.fetchone()[0]

		return cls.find(product_id)

	##########################
	# PRODUCT MODIFY METHODS #
	##########################

	def save(self):
		_conn.execute('''UPDATE tbl_products SET name = ?, image = ?, link = ?, description = ?, price = ? WHERE rowid = ?''', (self.name, self.image, self.link, self.description, self.price, self.product_id))
		_conn.commit()

	def delete(self):
		_conn.execute('''DELETE FROM tbl_products WHERE rowid = ?''', (self.product_id,))
		_conn.commit()


class Wishlist:
	def __init__(self, wish_id, list_name, user):
		self.wish_id = wish_id
		self.list_name = list_name
		self.user = user

	#################
	# CLASS METHODS #
	#################

	@classmethod
	def find(cls, wish_id):
		cur = _conn.execute('''SELECT wish_id, list_name, user_id FROM tbl_wish_list WHERE wish_id = ? LIMIT 1''', (wish_id,))

		wish_id, list_name, user_id = cur.fetchone()
		user = User.find_uid(user_id)

		return cls(wish_id, list_name, user)

	@classmethod
	def create(cls, list_name, user):
		_conn.execute('''INSERT INTO tbl_wish_list (list_name, user_id) VALUES (?, ?)''', (list_name, user.user_id))
		_conn.commit()

		cur = _conn.execute('''SELECT last_insert_rowid()''')
		wish_id = cur.fetchone()[0]

		return cls.find(wish_id)

	###########################
	# WISHLIST MODIFY METHODS #
	###########################

	def delete(self):
		_conn.execute('''DELETE FROM tbl_wish_list WHERE wish_id = ?''', (self.wish_id,))
		_conn.commit()

	def save(self):
		_conn.execute('''UPDATE tbl_wish_list SET list_name = ?, user_id = ? WHERE wish_id = ?''', (self.list_name, self.user.user_id, self.wish_id))
		_conn.commit()

	def add_item(self, product):
		_conn.execute('''INSERT INTO tbl_list_item (product_id, list_id, checked) VALUES(?, ?, 0)''', (product.product_id, self.wish_id))
		_conn.commit()

	def delete_item(self, product_id):
		_conn.execute('''DELETE FROM tbl_list_item WHERE list_id = ? AND product_id = ?''', (self.wish_id, product_id))
		_conn.commit()

	##########################
	# WISHLIST QUERY METHODS #
	##########################

	def get_items(self):
		cur = _conn.execute('''SELECT p.rowid AS product_id, p.name, p.image, p.link, p.description, p.price, i.checked
								FROM tbl_list_item AS i
								JOIN tbl_products AS p ON i.product_id = p.rowid
								JOIN tbl_wish_list AS w ON i.list_id = w.wish_id
								WHERE w.wish_id = ?''', (self.wish_id,))
		rows = cur.fetchall()

		items = []
		for row in rows:
			p = Product(*row)
			items.append(p)

		return items

####USERS####

#find a user
#uf = User.find_user("matN")
#u = User.find_user("bazS")
#print(u.find_friends())

#get the user's wishlist



#create a user
#u = User.create_user("Poo", "Nick", "Winnie12", "akdjsrgsegrsedfsd@poo.com", "12234")
#check a password
#print(User.check_password("Winnie12","12234"))

#delete a user
#User.delete_user("matN")


####PRODUCTS####
#find product
#p = Product.find_product(1)

#create a product
#p = Product.create_product("blah.jpg", "http://teamfourftw.com", "blah", "This is a description", 100000)

####WISHLIST####


#create a wishlist
#u = User.find_user("karB")
#w = u.create_wish_list("birthday")

#delete the wishlist
#u.delete_wish_list("birthday")

#gets a user's wishlists
#w = u.get_user_wish_lists()

#gets all products for a specific wishlist
#print(w.get_wish_list_products()[0].name)


####LIST ITEM####
#Add a list item
#w.add_list_item(1)


#get all products of a specific list
#print(w.get_wish_list_products())
