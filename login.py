import epyc
import re

from tornado.ncss import Server
#from db.password import hash_password, generate_salt
from db.api import User, Wishlist, UserNotFound

# decorator function for checking that the user is logged in
def logged_in(fn):
	def inner(response, *args, **kwargs):
		userid = response.get_secure_cookie('userid')
		# if logged in then do function
		if userid:
			return fn(response, *args, **kwargs)
		# if NOT logged in then display login page
		return response.redirect('/login')
	return inner

def get_current_user(response):
	userid = response.get_secure_cookie('userid')

	if userid:
		userid = userid.decode("utf-8")
	else:
		userid = None

	return userid

#@logged_in
def is_current_users_wishlist_page(response, username):
	if get_current_user(response) == username:
		return True
	return False


#commented out as we don't want landing page to be login page
#def home(response):
#	if response.get_secure_cookie('userid') is None:
#		response.redirect('/login')
#	else:
#		response.write('hello world')

@logged_in
def hello(response):
	response.write('''
	<html>
	<header>:)</header>
	<body>
	<h1>Hellos peoples of the internets</h1>
	</body>
	</html>
''')

def login(response):
	uid = response.get_field("uid")
	pwd = response.get_field("pwd", strip=False)
	userid = response.get_secure_cookie('userid')

	# already logged in!
	if userid:
		response.redirect('/users/' + userid.decode('utf-8'))
		return

	elif uid is None or pwd is None:
		response.write(epyc.render("templates/login.html",{"logged_in":get_current_user(response)}))
		return

	errors = []

	if not uid or not pwd:
		errors.append("Empty username or password")
		scope = {"errors": errors, "logged_in": get_current_user(response)}
		response.write(epyc.render("templates/login.html", scope))

	elif not User.check_password(uid, pwd):
		errors.append("Incorrect username or password")
		scope = {"errors": errors, "logged_in": get_current_user(response)}
		response.write(epyc.render("templates/login.html", scope))

	else:
		response.set_secure_cookie('userid', uid)
		response.redirect('/users/%s' % uid)

def logout(response):
	response.clear_cookie("userid")
	response.redirect('/')

##	userid=response.get_secure_cookie('userid')
##	if userid is None:
##		response.redirect('/login')
##	else:
##		response.clear_cookie('userid')
##		response.redirect('/login')
##class User:
##	def __init__(self, user, password):
##		self.user=user
##		self.password=password
##	def pas(self):
##		pas=self.password
##	def user(self):
##		user=self.user
##	def login(user,pas):
##		if user in users and pas in passw:
##			return True


def signup(response):
	fname = response.get_field("fname")
	lname = response.get_field("lname")
	email = response.get_field("email")
	username = response.get_field("username")
	password = response.get_field("password")
	# response.redirect('/login')
	# check for invalid input

	errors = []

	if not fname:
		errors.append("First name required")
	if not lname:
		errors.append("Last name required")
	if not re.match("^[-a-zA-Z0-9\+\._]+@([-a-zA-Z0-9]+\.)+[a-zA-Z]+$",email):
		errors.append("Valid email address required")
	if not re.match("^[a-zA-Z0-9_]+$", username):
		errors.append("Username can only contain letters, numbers or underscores")
	if len(password) < 6:
		errors.append("Password must be longer than 5 characters")

	if not errors:
		try:
			User.find(username)
		except UserNotFound:
			pass
		else:
			errors.append("Username is taken")

	if errors:
		scope = {
			"errors": errors,
			"logged_in": get_current_user(response),
			"fname": fname,
			"lname": lname,
			"email": email,
			"username": username
		}

		response.write(epyc.render("templates/login.html", scope))

	else:

		user = User.create(fname, lname, username, email, password)
		response.set_secure_cookie('userid', user.username)

		listname = "{}'s wishlist'".format(user.username)
		Wishlist.create(listname, user)

		response.redirect('/users/' + user.username)

if __name__ == '__main__':
	server=Server()
	#server.register('/home',home)
	server.register('/', hello)
	server.register('/login', login)
	server.register('/logout', logout)
	server.register('/signup',signup)
	server.run()
