# -*- coding: utf-8 -*-
#
# python wrapper for word query from synonymo.fr
# Author:       Eloi perdereau [[eloi@perdereau.eu][E-mail]]


try:
    from urllib2 import urlopen
    from urllib2 import URLError, HTTPError
    from StringIO import StringIO
    from HTMLParser import HTMLParser
except ImportError:
    from urllib.request import urlopen
    from urllib.error import URLError, HTTPError
    from io import StringIO
    from html.parser import HTMLParser

import re
import socket
from ..tq_common_lib import fixurl, decode_utf_8, get_variable

identifier="synonymo_fr_htmlparser"
language="fr"

_timeout_period_default = 10.0

try:
    from html import unescape
except ImportError:
    try:
        from html.parser import HTMLParser
    except ImportError:
        from HTMLParser import HTMLParser
    unescape = HTMLParser().unescape

def query(target, query_method="synonym"):
    ''' return result as list. relavance from high to low in each PoS.
Lookup routine for openthesaurus.de. When query_from_source is called, return:
   [status, [[PoS, [word_0, word_1, ...]],  [PoS, [word_0, word_1, ...]], ...]]
status:
    0: normal,  result found, list will be returned as a nested list
    1: normal, result not found, return empty list
    -1: unexpected result from query, return empty list
nested list = [PoS, list wordlist]
    Classifier('str'): Identifier to classify the resulting wordlist suits.
    wordlist = [word_0, word_1, ...]: list of words belonging to a same definition
    '''
    target=target.replace(u" ", u"+")
    result_list=_synonymo_fr_wrapper(target, query_method=query_method)
    if result_list == -1:
        return [-1, []]
    elif result_list == 1:
        return [1, []]
    else:
        return _parser(result_list)


def _synonymo_fr_wrapper(target, query_method='synonym'):
    '''
    query_method:
        synonym anyonym
    '''
    time_out_choice = float(get_variable(
        'tq_online_backends_timeout', _timeout_period_default))
    case_mapper={"synonym":u"syno",
                 "antonym":u"anto",
                }

    try:
        response = urlopen(fixurl(
            u'http://synonymo.fr/{0}/{1}'.format(
                case_mapper[query_method], target
                )).decode('ASCII'), timeout = time_out_choice)
        web_content = StringIO(unescape(decode_utf_8(response.read())))
        response.close()
    except HTTPError:
        return 1
    except URLError as err:
        if isinstance(err.reason, socket.timeout):  # timeout error?
            return 1
        return -1   # other error
    except socket.timeout:  # timeout error failed to be captured by URLError
        return 1
    return web_content


def extract_fiche(web_content, pointer, end):
    line_curr = web_content.readline()
    has_no_result = re.search("<h1>Aucun résultat.*</h1>", line_curr, re.UNICODE)
    has_result = re.search("<h1>Synonymes de.*</h1>", line_curr, re.UNICODE)
    if has_no_result:
        return [1, []]  # no synonym found on synonymo.fr
    if not has_result:
        # first line after class="fiche" should be <h1>
        return [-1, []]
    synonym_list = []
    while pointer<end:
        line_curr = web_content.readline()
        syno_mark = re.search("<a class=\"word\" href=\"[^\"]*\" title=\"[^\"]*\">([^<]*)</a>", line_curr, re.UNICODE)
        end_mark = re.search("<p class=\"links\">", line_curr, re.UNICODE)
        if syno_mark:
            synonym_list.append(syno_mark.group(1))
        if end_mark:
            if synonym_list:
                return [0, [ ['', synonym_list] ]]
            else:
                # syno_mark didn't get anything, source may have changed
                return [-1, []]
        pointer=web_content.tell()
    return [-1, []] # end mark not found, source may have changed


def _parser(web_content):
    pointer = web_content.tell()
    end = len(web_content.getvalue())
    while pointer<end:
        line_curr = web_content.readline()
        pointer=web_content.tell()
        found_fiche = re.search("<div class=\"fiche\">", line_curr, re.UNICODE)
        if found_fiche:
            synonym_list = extract_fiche(web_content, pointer, end)
            web_content.close()
            return synonym_list
    # class="fiche" not found, synonymo.fr source may have change
    web_content.close()
    return [-1, []]
