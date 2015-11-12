import urllib
import urllib2

def post_to_server(url, params):

	response=urllib2.urlopen(url,params).read()
	return response
