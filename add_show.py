import yaml

while True:
    d = {}
    d['title'] = raw_input('Title? ')
    slug = ''
    for c in d['title']:
        if c.isalpha():
            slug += c
    d['url'] = raw_input('Url? ')

    yaml.dump(d, open(slug + '.yaml', 'w'))
