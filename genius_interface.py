#!/usr/bin/python
import json
import re
import yaml
import urllib2

EMBED_PATTERN = 'http://genius.com/songs/%s/embed.js'
JSON_PATTERN = re.compile("JSON\.parse\('(.*)'\)\)\s+document.write", re.DOTALL)
SPLIT_LINE = re.compile('(\[[^\]]+)\n([^\]]+\])')

JSON_REPLACEMENTS = [('\\"', '"'), ('\\\\', '\\'), ('\\n', '\n'), ('\\/', '/'), ('\\"', '"'), ("\\'", "'"),
                     ('<p>', '\n'), ('</p>', '<br>'), ('\n ', '\n')]

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
    print 'Downloading %s...' % url
    opener = urllib2.build_opener()
    opener.addheaders = [('User-Agent', 'Mozilla/5.0')]
    response = opener.open(url)
    return response.read()


def get_tracklist(url):
    html_doc = download_url(url)
    # with open('temp.html', 'w') as f:
    #    f.write(html_doc)
    # exit(0)
    # html_doc = open('temp.html').read()
    if False:
        i = html_doc.index('<meta itemprop="page_data"')
        i2 = html_doc.index('\n', i)
    else:
        i2 = html_doc.index('itemprop="page_data"')
        i = html_doc.rfind('<meta ', 0, i2)
    s = html_doc[i:i2]
    key1 = 'content="'
    s = s[s.index(key1) + len(key1): -2]
    ss = s.replace('&quot;', '"')

    tracks = []
    JS = json.loads(ss)
    if 'album_appearances' not in JS:
        import pprint
        pprint.pprint(JS)
        exit(0)
    d = JS['album_appearances']
    for song in d:
        D = {}
        D['genius_id'] = str(song['song']['id'])
        song['song']['title'] = song['song']['title'].replace('&#39;', "'")
        D['title'] = str(song['song']['title'].encode('ascii', 'ignore'))
        D['track_no'] = int(song['track_number'] or 100)
        tracks.append(D)
    return tracks

def embed_to_clean_text(text):
    m = JSON_PATTERN.search(text)
    json_s = m.group(1)

    for a, b in JSON_REPLACEMENTS:
        json_s = json_s.replace(a, b)

    KEY1 = '<div class="rg_embed_body">'
    KEY2 = '</div>'

    body = json_s[json_s.index(KEY1) + len(KEY1):]
    body = body[:body.index(KEY2)]
    while '<a ' in body:
        i = body.index('<a ')
        i2 = body.index('>', i)
        i3 = body.index('</a>', i2)
        body = body[:i] + body[i2 + 1:i3] + body[i3 + 4:]

    for a, b in REPLACEMENTS.iteritems():
        body = body.replace(a, b)

    while True:
        m = SPLIT_LINE.search(body)
        if m:
            body = body.replace(m.group(0), m.group(1) + m.group(2))
        else:
            break

    return body


if __name__ == '__main__':
    import argparse
    import os.path
    parser = argparse.ArgumentParser()
    parser.add_argument('config', nargs='+')
    parser.add_argument('-l', '--list', action='store_true')
    parser.add_argument('-d', '--download_songs', action='store_true')
    parser.add_argument('-f', '--force', action='store_true')

    args = parser.parse_args()
    for config in args.config:
        slug = os.path.splitext(config)[0]
        if not os.path.exists(slug):
            os.mkdir(slug)
        config = yaml.load(open(config))

        if args.list:
            for track in get_tracklist(config['url']):
                fn = '%s/%02d-%s.yaml' % (slug, track['track_no'], re.sub(r'\W+', '', track['title']))
                print 'Creating', fn
                yaml.dump(track, open(fn, 'w'))

        for song in sorted(os.listdir(slug)):
            fn = os.path.join(slug, song)
            song_config = yaml.load(open(fn))
            if args.download_songs:
                if 'raw_text' not in song_config or args.force:
                    s = download_url(EMBED_PATTERN % song_config['genius_id'])
                    song_config['raw_text'] = embed_to_clean_text(s)
            yaml.dump(song_config, open(fn, 'w'))
