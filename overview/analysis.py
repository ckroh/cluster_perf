
from overview.models import *
from scipy.optimize import curve_fit
import numpy as np
from scipy import asarray as ar,exp
import scipy.stats as stats    
import scipy.special as scispec    
import math
from lmfit import Model,Parameters
from numpy import sqrt, pi, exp, linspace, loadtxt
#from scipy.stats import beta


def gauss_model(x, y, lnspc):	
	def gaussian(x, amp, cen, wid):
		"1-d gaussian: gaussian(x, amp, cen, wid)"
		return (amp/(sqrt(2*pi)*wid)) * exp(-(x-cen)**2 /(2*wid**2))
		
		
	gmodel = Model(gaussian)
	
	mean = sum(x*y) / sum(y)  
	sigma = np.sqrt(sum(y * (x - mean)**2) / sum(y))
	result = gmodel.fit(y, x=x, amp=max(y), cen=mean, wid=sigma)
	logging.debug("gauss fit result %s", result.fit_report())
	logging.debug("gauss fit result y %s", result.best_fit)
	
#	popt=result.params
	popt=[]
	for n in result.params.valuesdict():
		popt.append(result.params.valuesdict()[n])
	mu = popt[1]
	dev=popt[2]
	logging.debug("gauss fit popt %s",popt)
	display_x=x
	display_x=np.append([round(mu-4*dev, 4), round(mu-3*dev, 4), round(mu-2*dev, 4), round(mu-1.4*dev, 4), round(mu-1*dev, 4), round(mu-0.3*dev, 4), round(mu+0.3*dev, 4), round(mu, 4)], display_x)
	display_x=np.append(display_x, [round(mu+1*dev, 4), round(mu+1.4*dev, 4), round(mu+2*dev, 4), round(mu+3*dev, 4), round(mu+4*dev, 4)])
	
	display_y = []
	display_x=np.sort(display_x)
	for i in display_x:
		display_y.append(gaussian(i,*popt))
	return gaussian, popt, display_x, display_y
	
#	def func(x, a, b, c):
#		return a*np.exp(-(x - b)**2 / (2 * c**2))
#   
#	try:
##		p0=[max(y),mean,sigma],
#		popt,pcov = curve_fit(func, x, y, maxfev=5000)
#	except:				
#		logging.error("node analysis curve fit overflow") 
#		return None, None
#	
#	mu = popt[1]
#	dev = popt[2]
#	display_x=x
#	display_x=np.append([round(mu-4*dev, 4), round(mu-3*dev, 4), round(mu-2*dev, 4), round(mu-1.4*dev, 4), round(mu-1*dev, 4), round(mu-0.3*dev, 4), round(mu+0.3*dev, 4), round(mu, 4)], display_x)
#	display_x=np.append(display_x, [round(mu+1*dev, 4), round(mu+1.4*dev, 4), round(mu+2*dev, 4), round(mu+3*dev, 4), round(mu+4*dev, 4)])
#	
#	display_y = []
#	display_x=np.sort(display_x)
#	for i in display_x:
#		display_y.append(func(i,*popt))
#	return func, popt, display_x, display_y


#	yfit =[]
#	for i,j in zip(x,y):
#		yfit.extend([round(i,4)]*j)
#	logging.debug("yfit %s", yfit)
#	m, s = stats.norm.fit(yfit) # get mean and standard deviation  
#	pdf_g = stats.norm.pdf(lnspc, m, s)
#	logging.debug("analysis_node request normal dist fitted y values '%s' with mean %s and variance %s for lnspc %s", pdf_g, m, s, lnspc)
#	display_x=x
#	display_y = []
#	for i in display_x:
#		display_y.append(stats.norm.pdf(i, m, s))
#	return pdf_g, [0,m, s], display_x, display_y
		
def chisquared_model(x, y, lnspc):
	def chisquared(x, k):
		return (x**(k/2-1)*x*np.exp(-x/2))/(2**(k/2)*scispec.gamma(k/2))

	gmodel = Model(chisquared)
	
	
	result = gmodel.fit(y, x=x, k=2.5)
	logging.debug("chisquared fit result %s", result.fit_report())
	logging.debug("chisquared fit result y %s", result.best_fit)
	
#	popt=result.params
	popt=[]
	for n in result.params.valuesdict():
		popt.append(result.params.valuesdict()[n])
#	mu = popt[1]
#	dev=popt[2]
	logging.debug("beta fit popt %s",popt)
	display_x=x
#	display_x=np.append([round(mu-4*dev, 4), round(mu-3*dev, 4), round(mu-2*dev, 4), round(mu-1.4*dev, 4), round(mu-1*dev, 4), round(mu-0.3*dev, 4), round(mu+0.3*dev, 4), round(mu, 4)], display_x)
#	display_x=np.append(display_x, [round(mu+1*dev, 4), round(mu+1.4*dev, 4), round(mu+2*dev, 4), round(mu+3*dev, 4), round(mu+4*dev, 4)])
	
	display_y = []
	display_x=np.sort(display_x)
	for i in display_x:
		display_y.append(chisquared(i,*popt))
		
	popt.append(1)
	popt.append(1)
	return chisquared, popt, display_x, display_y
	
	
	
		
#def beta_model(x, y, lnspc):
#	def beta(x, a, b):
#		return scispec.gamma(a) * scispec.gamma(b) / scispec.gamma(a+b)  

#	gmodel = Model(beta)
#	
#	result = gmodel.fit(y, x=x, a=1.0, b=0.0)
#	logging.debug("beta fit result %s", result.fit_report())
#	logging.debug("beta fit result y %s", result.best_fit)
#	
##	popt=result.params
#	popt=[]
#	for n in result.params.valuesdict():
#		popt.append(result.params.valuesdict()[n])
#	mu = popt[1]
#	dev=popt[2]
#	logging.debug("beta fit popt %s",popt)
#	display_x=x
#	display_x=np.append([round(mu-4*dev, 4), round(mu-3*dev, 4), round(mu-2*dev, 4), round(mu-1.4*dev, 4), round(mu-1*dev, 4), round(mu-0.3*dev, 4), round(mu+0.3*dev, 4), round(mu, 4)], display_x)
#	display_x=np.append(display_x, [round(mu+1*dev, 4), round(mu+1.4*dev, 4), round(mu+2*dev, 4), round(mu+3*dev, 4), round(mu+4*dev, 4)])
#	
#	display_y = []
#	display_x=np.sort(display_x)
#	for i in display_x:
#		display_y.append(gaussian(i,*popt))
#	return beta, popt, display_x, display_y
	
	
	

def gamma_model(x, y, lnspc):
	def gamma(x, a, b):
		return (b**a * x**(a-1) * np.exp(-b*x))/scispec.gamma(a)	
#		return 1/(scispec.gamma(a)*b**a)*x**(a-1)*np.exp(-x/b)

	gmodel = Model(gamma)
	params = Parameters()
	params.add('a', value=2.5, min=0)
	params.add('b', value=5, min=0)
	
	result = gmodel.fit(y, x=x, params=params)
	logging.debug("gamma fit result %s", result.fit_report())
	logging.debug("gamma fit result y %s", result.best_fit)
	
#	popt=result.params
	popt=[]
	for n in result.params.valuesdict():
		popt.append(result.params.valuesdict()[n])
#	mu = popt[1]
#	dev=popt[2]
	logging.debug("gamma fit popt %s",popt)
	display_x=x
#	display_x=np.append([round(mu-4*dev, 4), round(mu-3*dev, 4), round(mu-2*dev, 4), round(mu-1.4*dev, 4), round(mu-1*dev, 4), round(mu-0.3*dev, 4), round(mu+0.3*dev, 4), round(mu, 4)], display_x)
#	display_x=np.append(display_x, [round(mu+1*dev, 4), round(mu+1.4*dev, 4), round(mu+2*dev, 4), round(mu+3*dev, 4), round(mu+4*dev, 4)])
	
	display_y = []
	display_x=np.sort(display_x)
	for i in display_x:
		display_y.append(chisquared(i,*popt))
		
	popt.append(1)
	popt.append(1)
	return gamma, popt, display_x, display_y
	
def lognormal_model(x, y, lnspc):
	def lognormal(x, shape, location, scale):
		return (1/((x-location)*shape*np.sqrt(2*np.pi)))*np.exp(-(np.log(x-location)-np.log(scale))**2/(2*shape**2))
#		return 1/(x*sigma*amp) * np.exp(-(np.log(x)-mu)**2/2*sigma**2)
#		return 1/(scispec.gamma(a)*b**a)*x**(a-1)*np.exp(-x/b)

	mean = sum(x*y) / sum(y) 
	scale=mean
	
	sigma = np.sqrt(sum(y * (x - mean)**2) / sum(y))
	#sigma = 0.5
	gmodel = Model(lognormal)
	
	
	result = gmodel.fit(y, x=x, shape=sigma, location=0, scale=scale)
	logging.debug("lognormal fit result %s", result.fit_report())
	logging.debug("lognormal fit result y %s", result.best_fit)
	
#	popt=result.params
	popt=[]
	for n in result.params.valuesdict():
		popt.append(result.params.valuesdict()[n])
	mu = popt[1]
	dev=popt[2]
	logging.debug("lognormal fit popt %s",popt)
	display_x=x
#	display_x=np.append([round(mu-4*dev, 4), round(mu-3*dev, 4), round(mu-2*dev, 4), round(mu-1.4*dev, 4), round(mu-1*dev, 4), round(mu-0.3*dev, 4), round(mu+0.3*dev, 4), round(mu, 4)], display_x)
#	display_x=np.append(display_x, [round(mu+1*dev, 4), round(mu+1.4*dev, 4), round(mu+2*dev, 4), round(mu+3*dev, 4), round(mu+4*dev, 4)])
	
	display_y = []
	display_x=np.sort(display_x)
	for i in display_x:
		display_y.append(lognormal(i,*popt))
		
	return lognormal, popt, display_x, display_y
	
    
def node_data(x, y, model=None):
	if model is None:
		model=5	
	models = {
		1: gauss_model,
		2: gamma_model,
#		3: beta_model,
		4: chisquared_model,
		5: lognormal_model,
	}
	
	xmin, xmax = min(x), max(x)
	lnspc = np.linspace(xmin, xmax, len(y))
	
	display_y = []
	func, popt, display_x, display_y = models[model](x, y, lnspc)
	
	return display_x, display_y, popt
	
	
	
	
#	aa=[]
#	aaa=[]
#	for k in results:
#		aa.append((float(k['norm_result']), k['count']))
#	aaa=sorted(aa, key=lambda x: x[0])
#	ax=[]
#	ay=[]
#	maxx=0
#	maxy=0
#	for k,v in aaa:
#		ax.append(k)
#		ay.append(v)
#	
#	x=np.array(ax)
#	y=np.array(ay)
