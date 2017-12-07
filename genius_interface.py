#!/usr/bin/python
import bs4
from bs4 import BeautifulSoup
import json
import re, yaml
import urllib2
from util import all_sections

EMBED_PATTERN = 'http://genius.com/songs/%s/embed.js'
JSON_PATTERN = re.compile("JSON\.parse\('(.*)'\)\)\s+document.write", re.DOTALL)
SPLIT_LINE = re.compile('(\[[^\]]+)\n([^\]]+\])')
CHAR_LINE = re.compile('\[([^\]]+)\]')
LOWERCASE = re.compile('[a-z]')
STAGE_DIRECTION = [
    re.compile('\(<i>([^<]+)</i>\)'),
    re.compile('<i>\(([^\)]+)\)</i>'),
    re.compile('\(([^\)]+)\)'),
    re.compile('<b>\[([^\]]+)\]</b>'),
    re.compile('<i>\[([^\]]+)\]</i>'),
]
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
    print 'Downloading %s...'%url
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
    #with open('temp.html', 'w') as f:
    #    f.write(html_doc)
    #exit(0)
    #html_doc = open('temp.html').read()
    if False:
        i = html_doc.index('<meta itemprop="page_data"')
        i2 = html_doc.index('\n', i)
    else:
        i2 = html_doc.index('itemprop="page_data"')
        i = html_doc.rfind('<meta ', 0, i2)
    s = html_doc[i:i2]
    key1 = 'content="'
    s = s[ s.index(key1)+len(key1): -2]
    ss = s.replace('&quot;', '"')

    tracks = []
    JS = json.loads(ss)
    if 'album_appearances' not in JS:
        import pprint
        pprint.pprint(JS)
        exit(0)
    d= JS['album_appearances']
    for song in d:
        D = {}
        D['genius_id'] = str(song['song']['id'])
        D['title'] = str(song['song']['title'].encode('ascii', 'ignore'))
        D['track_no'] = int(song['track_number'] or 100)
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

def parse_character_list(s, config):
    if ':' in s:
        s = s[s.index(':')+1:]
    if s in config['char_translations']:
        s = config['char_translations'][s]

    c = [s]
    splitters = config.get('splitters', [' & ', '/', ' AND '])
    for splitter in splitters:
        x = []
        for s in c:
            x += s.split(splitter)
        c = x
    full_list = []
    for ss in c:
        ss = ss.strip()
        if len(ss)==0:
            continue
        try:
            ss = str(ss)
        except:
            None
        if ss in config['char_translations']:
            full_list += parse_character_list(config['char_translations'][ss], config)
        else:
            full_list.append(ss)
    return full_list

def parse_characters(s, config):
    D = {}
    for direction in ['spoken', 'sung', 'on phone']:
        key = ', '+direction
        if key in s:
            s = s.replace(key, ' (%s)'%direction)
    s = s.upper()
    if s in config['char_translations']:
        s = config['char_translations'][s]
    m = PARENTHETICAL.match(s)
    if m:
        D.update(parse_characters(m.group(1), config))
        D['stage_direction'] = m.group(2)
        return D

    if 'EXCEPT' in s:
        s, _, except_s = s.partition('EXCEPT')
        D['except'] = parse_character_list(except_s, config)
    c = parse_character_list(s, config)
    if len(c)>0:
        D['characters'] = c
    return D

def create_entry(header, lines, sections):
    for i, line in enumerate(lines):
        try:
            lines[i] = str(line)
        except:
            None
    entry = {'lines': lines}
    if header is None:
        header = {}
    if 'characters' not in header and len(sections)>0:
        last_header = sections[-1].get('header', {})
        if 'characters' not in last_header and len(sections)>1:
            last_header = sections[-2].get('header', {})
        if 'characters' in last_header:
            header['characters'] =  list(last_header['characters'])
    if len(header)>0:
        entry['header']=header
    sections.append(entry)

def match_stage_direction(line):
    for pattern in STAGE_DIRECTION:
        m = pattern.match(line)
        if m:
            return m

def search_stage_direction(line):
    for pattern in STAGE_DIRECTION:
        m = pattern.search(line)
        if m:
            return m

def parse_lyrics(s, config):
    header = None
    sections = []
    lines = []
    table = []

    for a,b in config.get('global_translations', {}).iteritems():
        if a in s:
            s = s.replace(a,b)

    for line in s.split('\n'):
        line = line.strip()
        if len(line)==0:
            continue
        m0 = CHAR_LINE.match(line)
        m1 = match_stage_direction(line)
        m2 = '<table' in line

        if (m0 or m1 or m2) and len(lines)>0:
            create_entry(header, lines, sections)
            lines = []

        if len(table)>0:
            if '</table>' in line:
                table.append(line)
                table_s = '\n'.join(table)
                table = BeautifulSoup(table_s, 'html.parser')
                cols = []
                for row in table.find_all('tr'):
                    for i, cell in enumerate(row.find_all('td')):
                        if i >= len(cols):
                            cols.append([])
                        cols[i].append(cell.text)
                chunks = []
                for col in cols:
                    chunks.append(parse_lyrics('\n'.join(col), config))
                sections.append({'simultaneous': chunks})
                table = []
            else:
                table.append(line)
        elif m0:
            header = {}

            char_s = m0.group(1)
            m = search_stage_direction(char_s)
            if m:
                char_s = char_s.replace(m.group(0), '').strip()
                header['stage_direction'] = m.group(1)

            if config.get('require_caps_characters', False) and LOWERCASE.search(char_s):
                sd = header.get('stage_direction', '') + char_s
                sections.append({'stage_direction': sd})
                header = {}
            else:
                header.update( parse_characters(char_s, config))
        elif m1:
            sections.append({'stage_direction': m1.group(1)})
        elif m2:
            table.append(line)
        else:
            lines.append(line)
            #print line

    if len(lines)>0:
        create_entry(header, lines, sections)
    thus_far = set()
    both = None
    for section in all_sections(sections):
        chars = section.get('header', {}).get('characters', [])
        if chars == ['BOTH']:
            both = thus_far
            break
        thus_far.update(set(chars))

    if both and len(both)!=2:
        both = both - set(config.get('ignore_chars', []))
    if both and len(both)==2:
        print 'BOTH = ', both
        for section in all_sections(sections):
            chars = section.get('header', {}).get('characters', [])
            if chars == ['BOTH']:
                section['header']['characters'] = list(both)
    return sections

import argparse, os.path
parser = argparse.ArgumentParser()
parser.add_argument('config')
parser.add_argument('filter', nargs='?')
parser.add_argument('-l', '--list', action='store_true')
parser.add_argument('-d', '--download_songs', action='store_true')
parser.add_argument('-p', '--parse', action='store_true')
parser.add_argument('-f', '--force', action='store_true')

args = parser.parse_args()
slug = os.path.splitext(args.config)[0]
if not os.path.exists(slug):
    os.mkdir(slug)
config = yaml.load(open(args.config))

# Rewrite Equivalent Chars
if 'char_translations' not in config:
    config['char_translations'] = {}
for key, row in config.get('equivalent_chars', {}).iteritems():
    if type(row)==str:
        config['char_translations'][row] = key
    else:
        for a in row:
            config['char_translations'][a] = key

if args.list:
    for track in get_tracklist(config['url']):
        fn = '%s/%02d-%s.yaml'%(slug, track['track_no'], re.sub(r'\W+', '', track['title']))
        yaml.dump(track, open(fn, 'w'))

for song in sorted(os.listdir(slug)):
    fn = os.path.join(slug, song)
    if args.filter and args.filter not in fn:
        continue
    song_config = yaml.load(open(fn))
    if args.download_songs:
        if 'raw_text' not in song_config or args.force:
            s = download_url(EMBED_PATTERN % song_config['genius_id'])
            song_config['raw_text'] = embed_to_clean_text(s)
    if args.parse and 'raw_text' in song_config:
        song_config['lyrics'] = parse_lyrics(song_config['raw_text'], config)
    yaml.dump(song_config, open(fn, 'w'))
