from django import template
from collections import OrderedDict

register = template.Library()


@register.simple_tag
def url_replace(request, field, value):

	dict_ = request.GET.copy()

	dict_[field] = value

	return dict_.urlencode()
	
	

@register.simple_tag
def float_comp(f, s):

	if f<float(s):
		return True
	else:
		return False
		
		
@register.filter(name='sort')
def listsort(value):
	if isinstance(value,dict):
		new_dict = OrderedDict()
		key_list = value.keys()
		key_list.sort()
		for key in key_list:
			new_dict[key] = value[key]
		return new_dict
	elif isinstance(value, list):
		new_list = list(value)
		new_list.sort()
		return new_list
	else:
		return value
listsort.is_safe = True

@register.filter
def get_item(dictionary, key):
    return dictionary.get(key)
