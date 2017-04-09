#!/usr/bin/python
import bs4
from bs4 import BeautifulSoup
import re, yaml
import urllib2

EMBED_PATTERN = 'http://genius.com/songs/%s/embed.js'
JSON_PATTERN = re.compile("JSON\.parse\('(.*)'\)\)\s+document.write", re.DOTALL)
SPLIT_LINE = re.compile('(\[[^\]]+)\n([^\]]+\])')
CHAR_LINE = re.compile('\[([^\]]+)\]')
STAGE_DIRECTION = re.compile('\(<i>([^<]+)</i>\)')
PARENTHETICAL = re.compile('(.*)\((.*)\)')

REPLACEMENTS = {
    '\xe2\x80\x94': '-',
    '\xe2\x80\x98': "'",
    '\xe2\x80\x99': "'",
    '\xe2\x80\x9c': '"',
    '\xe2\x80\x9d': '"',
    '\xe2\x80\xa6': '...',
    '\xc2\xa0': ' ',
    '&amp;': '&',
    '<br>': '',
    '><table': '>\n<table',
    '<small>': '',
    '</small>': '',
}

def download_url(url):
    opener = urllib2.build_opener()
    opener.addheaders = [('User-Agent', 'Mozilla/5.0')]
    response = opener.open(url)
    return response.read()

def get_element(tag, subtype, attribute, value):
    for item in tag.find_all(subtype):
        if value in item.get(attribute, ''):
            return item

def get_tracklist(url):
    html_doc = download_url(url)
    #html_doc = open('Les-miserables-1987-original-broadway-cast')
    soup = BeautifulSoup(html_doc, 'html.parser')
    track_list = get_element(soup, 'ul', 'class', 'song_list')
    if track_list is None:
        return None
    tracks = []
    for item in track_list.children:
        if type(item)==bs4.element.NavigableString:
            continue
        D = {}
        id = item.get('data-id', '')
        if len(id)==0:
            continue
        D['genius_id'] = str(item['data-id'])
        title = get_element(item, 'span', 'class', 'song_title')
        if title:
            if title.text == str(title.text):
                D['title'] = str(title.text)
            else:
                D['title'] = title.text
        number = get_element(item, 'span', 'class', 'track_number')
        if number:
            text = number.text.replace('.', '')
            D['track_no'] = int(text)

        tracks.append(D)

    return tracks

def embed_to_clean_text(text):
    m = JSON_PATTERN.search(text)
    json_s = m.group(1)

    for a,b in [('\\"', '"'), ('\\\\', '\\'), ('\\n', '\n'), ('\\/', '/'), ('\\"', '"'), ("\\'", "'"), ('<p>', '\n'), ('</p>', '<br>'), ('\n ', '\n')]:
        json_s = json_s.replace(a,b)

    KEY1 = '<div class="rg_embed_body">'
    KEY2 = '</div>'

    body = json_s[ json_s.index(KEY1)+len(KEY1): ]
    body = body[ : body.index(KEY2)]
    while '<a ' in body:
        i = body.index('<a ')
        i2 = body.index('>', i)
        i3 = body.index('</a>', i2)
        body = body[:i] + body[i2+1:i3] + body[i3+4:]
        
    for a,b in REPLACEMENTS.iteritems():
        body = body.replace(a,b)
        
    while True:
        m = SPLIT_LINE.search(body)
        if m:
            body = body.replace(m.group(0), m.group(1)+m.group(2))
        else:
            break

    return body

def parse_character_list(s):
    if ':' in s:
        s = s[s.index(':')+1:]
    c = [s]
    for splitter in [' & ', '/', ' AND ']:
        x = []
        for s in c:
            x += s.split(splitter)
        c = x
    full_list = []
    for ss in map(str.strip, c):
        if len(ss)==0:
            continue
        #full_list += translate(ss.upper())
        full_list.append(ss.upper())
    #print full_list
    return full_list

def parse_characters(s):
    D = {}
    m = PARENTHETICAL.match(s)
    if m:
        D.update(parse_characters(m.group(1)))
        D.update(parse_characters(m.group(2)))
        return D
        
    if 'EXCEPT' in s:
        s, _, except_s = s.partition('EXCEPT')
        D['except'] = parse_character_list(except_s)
    c = parse_character_list(s)
    if len(c)>0:
        D['characters'] = c
    return D

def parse_lyrics(s):
    header = None
    sections = []
    lines = []
    table = []

    for line in s.split('\n'):
        line = line.strip()
        if len(line)==0:
            continue
        m0 = CHAR_LINE.match(line)
        m1 = STAGE_DIRECTION.match(line)
        m2 = '<table' in line
        
        if (m0 or m1 or m2) and len(lines)>0:
            entry = {'lines': lines}
            if header:
                entry['header']=header
            sections.append(entry)
            lines = []
        
        if len(table)>0:
            if '</table>' in line:
                table.append(line)
                table_s = '\n'.join(table)
                
                chunks = []
                index = 0
                while '<td' in table_s[index:]:
                    i = table_s.index('<td', index)
                    i2 = table_s.index('>', i)
                    i3 = table_s.index('</td>', i2)
                    contents = table_s[i2+1:i3]
                    index = i3
                    chunks.append(parse_lyrics(contents))
                    #body = body[:i] + body[i2+1:i3] + body[i3+4:]
                sections.append({'simultaneous': chunks})
                table = []
            else:
                table.append(line)
        elif m0:
            header = {}
            
            char_s = m0.group(1)
            m = STAGE_DIRECTION.search(char_s)
            if m:
                char_s = char_s.replace(m.group(0), '').strip()
                header['stage_direction'] = m.group(1)
                
            header.update( parse_characters(char_s))
        elif m1:
            sections.append({'stage_direction': m1.group(1)})
        elif m2:
            table.append(line)
        else:
            lines.append(line)
            #print line

    if len(lines)>0:
        entry = {'lines': lines}
        if header:
            entry['header']=header
        sections.append(entry)
    return sections

import argparse, os.path
parser = argparse.ArgumentParser()
parser.add_argument('config')
parser.add_argument('-l', '--list', action='store_true')

args = parser.parse_args()
slug = os.path.splitext(args.config)[0]
if not os.path.exists(slug):
    os.mkdir(slug)
config = yaml.load(open(args.config))
if args.list:
    for track in get_tracklist(config['url']):
        fn = '%s/%02d-%s.yaml'%(slug, track['track_no'], re.sub(r'\W+', '', track['title']))
        yaml.dump(track, open(fn, 'w'))
        
#s = download_url(EMBED_PATTERN % '357017')
#x = embed_to_clean_text(s)
#print x
#import pprint
#pprint.pprint(parse_lyrics(x))