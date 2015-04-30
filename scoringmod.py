# File contains class definition and functions to calculate
# scores between author names

import re

class AuthorInfo:
    def __init__(self,init2,suffix,first,keywords):
        self.init2 = init2
        self.suffix = suffix
        self.first = first
        self.keywords = keywords
    
class AddressInfo:
    def __init__(self,fullAdd,email):
        self.fullAdd = fullAdd
        self.email = email

class ItemInfo:
    def __init__(self,title,lang,keywords,org,pref_name):
        self.title = title
        self.lang = lang 
        self.keywords = keywords
        self.org = org
        self.pref_name = pref_name

class IssueInfo:
    def __init__(self,title,subject,year):
        self.title = title
        self.subject = subject
        self.year = year

class CoAuthorInfo:
    def __init__(self,authors):
        self.authors = authors

class GroupInfo:
    def __init__(self,i,name,address,affiliation):
        self.i = i # group number
        self.name = name
        self.address = address
        self.affiliation = affiliation

def authorScore(a1, a2):
    init2, suffix, first = 0, 0, 0
    #print "Init2:\'%s\' \'%s\'"%(a1.init2,a2.init2)	
    if a1.init2.strip() == '' or a2.init2.strip() == '': init2 = 0
    elif a1.init2.lower().strip() == a2.init2.lower().strip() :
        #print "init2 match" 
        init2 = 5
    else : init2 = -10
    if a1.suffix.strip() == '' or a2.suffix.strip() == '': suffix = 0
    elif a1.suffix.lower().strip() == a2.suffix.lower().strip() : 
        #print "suffix match"
        suffix = 5
    else : suffix = -10

    #print "First:\'%s\' \'%s\'"%(a1.first,a2.first)	
    a1.first = a1.first.replace('.','').replace(',','').strip()
    a2.first = a2.first.replace('.','').replace(',','').strip()  
    if a1.first == '' or a2.first == '': first = 0
    else :
        f1 = a1.first.lower().split()
        f2 = a2.first.lower().split()
        try:
            if f1 and f2 and len(f1[0]) > 1 and len(f2[0]) > 1:
                if f1[0] == f2[0] : 
                    first = 5
                    #print "first match "
                else : first = -10
        except IndexError:
            print "IndexError", f1, f2
            raise IndexError
        if len(f1) > 1 and len(f2) > 1:
            if f1[1] == f2[1] and init2 == 0: 
                init2 = 5
                #print "init2 match 2"
            elif len(f1[1]) == 1 or len(f2[1]) == 1 and init2 == 0:
                try:
                    if f1[1][0] == f2[1][0]: 
                        init2 = 5
                        #print "init2 match 3"
                    else : init2 = -10
                except IndexError: 
                    print 'IndexError', f1, f2
                    raise IndexError
         
    keywords = len(a1.keywords & a2.keywords) * 5
    score = init2 + suffix + first + keywords
    if score > 10 : score = 10
    #if score < 0 : score = 0
    return score

def usAddress(full_address):
    '''Parses full_address string and extracts city, state and pin information '''
    csv = [x.strip() for x in full_address.split(',')]
    last_block = [x.strip() for x in csv[-1].split(' ')]
    city = csv[-2]
    state = last_block[0]
    if len(last_block[1]) == 5: pin = last_block[1]
    else: pin = '-1'
    return city, state, pin  

def addressScore(a1, a2):    
    stop = set(['all', 'sci', 'sch', 'just', 'when', 'coll', 'japan', 'its', 'biol', 'also', 'had', 'should', 'to', 'only', 'natl', 'has', 'might',
                'ca', 'do', 'them', 'his', 'get', 'cannot', 'every', 'they', 'not', 'fac', 'him', 'nor', 'd', 'like', 'did', 'technol', 'this', 'either',
                'div', 'where', 'because', 'says', 'often', 'med', 'some', 'likely', 'korea', 'are', 'dear', 'our', 'chem', 'canada', 'what', 
                'said', 'for', 'res', 'since', 'yet', 'state', 'does', 'got', 'neither', 'ever', 'across', 'she', 'be', 'we', 'who', 'however',
                'let', 'hosp', 'hers', 'by', 'on', 'about', 'would', 'ctr', 'of', 'could', '&', 'china', 'or', 'south', 'among', 'own', 'into', 
                'usa', 'least', 'twas', 'england', 'univ', 'your', 'he', 'from', 'her', 'whom', 'there', 'been', 'france', 'their', 'too', 'was', 
                'wants', 'that', 'but', 'else', 'with', 'than', 'spain', 'must', 'me', 'f', 'these', 'say', 'us', 'will', 'dept', 'while', 'r', 
                'can', 'were', 'my', 'and', 'engn', 'then', 'almost', 'is', 'am', 'it', 'an', 'as', 'at', 'have', 'in', 'clin', 'any', 'if', 'italy',
                'no', 'rather', 'able', 'tis', 'how', 'other', 'which', 
                'peoples', 'hlth', 'you', 'phys', 'mat', 'may', 'after', 'lab', 'most', 'inst', 'why', 'a', 'off', 'i', 'so', 'the', 'germany'])
    
    #Geo Address score
    fullAdd = 0
    if a1.fullAdd == ' ' or a2.fullAdd == ' ': fullAdd = 0
    elif a1.fullAdd[-4:] == ' USA' and a2.fullAdd[-4:] == ' USA':
        c1,s1,p1 = usAddress(a1.fullAdd.lower())
        c2,s2,p2 = usAddress(a2.fullAdd.lower())
        if s1 == s2 :
            fullAdd += 2
            if c1 == c2:
                fullAdd += 3
                if p1 == p2 : fullAdd += 5
    else:
        pat = re.compile('[/:()<>|?*,\'\"`-]') 
        ad1 = set(pat.sub(' ',a1.fullAdd).lower().split())
        ad2 = set(pat.sub(' ',a2.fullAdd).lower().split())
        fullAdd = len(ad1 & ad2 - stop)

    #Email address score
    email = 0
    if a1.email == ' ' or a2.email == ' ': email = 0
    elif a1.email.lower() == a2.email.lower() : email = 10
    else : email = -5
    #Total score
    score = fullAdd + email
    if score > 20 : score = 20
    #elif score < 0 : score = 0
    return score

def itemScore(a1, a2):
    base = set(['all', 'just', 'when', 'its', 'also', 'had', 'should', 'to', 'only', 'has', 'might',
                'do', 'them', 'his', 'get', 'cannot', 'every', 'they', 'not', 'him', 'nor', 'like',
                'did', 'this', 'either', 'where', 'because', 'says', 'often', 'some', 'likely', 'are',
                'dear', 'our', 'what', 'said', 'for', 'since', 'yet', 'does', 'got', 'neither', 'ever',
                'across', 'she', 'be', 'we', 'who', 'however', 'let', 'hers', 'by', 'on', 'about',
                'would', 'of', 'could', '&', 'or', 'among', 'own', 'into', 'least', 'twas', 'your', 'he',
                'from', 'her', 'whom', 'there', 'been', 'their', 'too', 'was', 'wants', 'that', 'but',
                'else', 'with', 'than', 'must', 'me', 'these', 'say', 'us', 'will', 'while', 'can',
                'were', 'my', 'and', 'then', 'almost', 'is', 'am', 'it', 'an', 'as', 'at', 'have', 'in',
                'any', 'if', 'no', 'rather', 'able', 'tis', 'how', 'other', 'which', 'you', 'may',
                'after', 'most', 'why', 'a', 'off', 'i', 'so', 'the'])
    stop_org = set(['med', 'calif', 'sci', 'ctr', 'res', 'coll', 'state', 'acad', 'inst', 'hosp', 'natl', 'technol', 'univ'])
    pat = re.compile('[/:()<>|?*,\'\"`-]')
    t1 = set(pat.sub(' ',a1.title).lower().split())
    t2 = set(pat.sub(' ',a2.title).lower().split())
    o1, o2 = set(), set()
    for o in a1.org: o1.update(pat.sub(' ',o).lower().split())
    for o in a2.org: o2.update(pat.sub(' ',o).lower().split())

    title = len(t1 & t2 - base)
    #print t1 & t2 - base

    lang_set = a1.lang & a2.lang
    lang = 0
    if len(lang_set) == 0 : lang = 0
    elif 'EN English' in lang_set and len(lang_set) == 1 : lang = 1
    else : lang = 3
    #print lang
    # Language seems irrelevant. Removing Language score 
    lang = 0
    
    keywords = len(a1.keywords & a2.keywords) * 5  
    #print a1.keywords & a2.keywords

    org = len(o1 & o2 - base - stop_org)
    #print o1 & o2 - base - stop_org
  
    pref_name = 0
    if len(a1.pref_name & a2.pref_name) > 0 : pref_name = 5
    #print a1.pref_name & a2.pref_name

    score = title + lang + keywords + org + pref_name
    if score > 15 : score = 15
    return score     

def issueScore(a1, a2):
    stop_title = set(['all', 'just', 'when', 'its', 'also', 'had', 'should', 'to', 'only', 'has', 'might',
                'do', 'them', 'his', 'get', 'cannot', 'every', 'they', 'not', 'him', 'nor', 'like',
                'did', 'this', 'either', 'where', 'because', 'says', 'often', 'some', 'likely', 'are',
                'dear', 'our', 'what', 'said', 'for', 'since', 'yet', 'does', 'got', 'neither', 'ever',
                'across', 'she', 'be', 'we', 'who', 'however', 'let', 'hers', 'by', 'on', 'about',
                'would', 'of', 'could', '&', 'or', 'among', 'own', 'into', 'least', 'twas', 'your', 'he',
                'from', 'her', 'whom', 'there', 'been', 'their', 'too', 'was', 'wants', 'that', 'but',
                'else', 'with', 'than', 'must', 'me', 'these', 'say', 'us', 'will', 'while', 'can',
                'were', 'my', 'and', 'then', 'almost', 'is', 'am', 'it', 'an', 'as', 'at', 'have', 'in',
                'any', 'if', 'no', 'rather', 'able', 'tis', 'how', 'other', 'which', 'you', 'may',
                'after', 'most', 'why', 'a', 'off', 'i', 'so', 'the', 'journal', 'research', 'international', 'science'])    
    if a1.title == a2.title: score = 5
    else:
        pat = re.compile('[/:()<>|?*,\'\"`-]')
        t1 = set(pat.sub(' ',a1.title).lower().split())
        t2 = set(pat.sub(' ',a2.title).lower().split())
        title = len(t1 & t2 - stop_title)
        subject = len(a1.subject & a2.subject)
        score = title + subject
        if score > 5 : score = 5
    return score 

def coAuthorScore(a1,a2):
    sim = len(a1.authors & a2.authors)
    score = 0
    if sim == 1 : score = 5
    elif sim == 2 : score = 8
    elif sim > 2 : score = 10
    return score

def citeScore(a1,a2,cur):
    count = 0
    cur.execute("SELECT 1 FROM Citation_Found WHERE item_citing=(%s) AND item_cited=(%s);",(a1,a2))
    count += cur.rowcount
    cur.execute("SELECT 1 FROM Citation_Found WHERE item_citing=(%s) AND item_cited=(%s);",(a2,a1))
    count += cur.rowcount
    if count > 0 : return 10
    else : return 0 

def interaction(ait1,ait2,ais1,ais2,ac1,ac2):
    '''
       Calculates interaction score.
       5 points for sharing pref_name and issue subject
       5 points for sharing coauthor name_hash and issue subject 
    '''
    coauthor = len(ac1.authors & ac2.authors)
    subject = len(ais1.subject & ais2.subject)
    pref_name = len(ait1.pref_name & ait2.pref_name)
    score1, score2 = 0, 0
    if subject & pref_name: score1 = 5
    if subject & coauthor: score2 = 5
    return score1 + score2 
