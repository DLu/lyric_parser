import yaml

slug = raw_input('Slug ')
d = {}
d['title'] = raw_input('Title? ')
d['url'] = raw_input('Url? ')

yaml.dump(d, open(slug + '.yaml', 'w'))
