# This script uses a bucketed author name to calculate pair-wise score. Outputs weighted edge pairs file.
import psycopg2
from itertools import combinations as comb
from itertools import product as prod
import subprocess
import os
import scoringmod as sm
from heapq import heappush, heappop
from collections import Counter
from math import ceil
import re

def isdigit(s):
    ''' Checks whether string <s> is an integer'''
    try:
        int(s)
        return True
    except ValueError:
        return False

def name(au):
    '''This function accepts AuthorInfo object and extracts 
       first name and second initial. The returned strings are devoid of
       periods, commas and are in lower case.
    '''
    s_i = au.init2.lower().strip()
    first_name, second_initial = '', s_i
    f_n = au.first.lower().strip()
    if f_n == '': pass
    else:
       f_n = [x.strip(',.') for x in f_n.strip(',. ').split()]
       if len(f_n[0]) > 1 : first_name = f_n[0]
       if len(f_n) > 1 and s_i == '': second_initial = f_n[1][0]
    return first_name, second_initial

#--Algorithm that finds connected components--#
def walk(s,G):
    '''Finds connected component containing node u
    '''
    P, Q = set([s]), set([s])
    while Q:
        u = Q.pop()
        for v in G[u].difference(P):
            Q.add(v)
            P.add(v)
    return P

def components(G):
    '''Finds connected components in graph G.
       Returns a list of sets.
    '''
    seen, comp = set(), list()
    for u in G:
        if u in seen : continue
        C = walk(u,G)
        seen.update(C)
        comp.append(C)
    return comp
#----#

def removeNode(e,group,wpairs):
    '''This function takes the negative weighted edge e, both of whose nodes belong to the same group
       and selects a node from removal from the group. 
       It selects node that has a smaller sum of edge weights to other nodes of that group.
    '''
    sum0, sum1 = 0,0
    for node in group:
        if node == e[0] or node == e[1] : pass
        else:
            w = 0
            if (e[0],node) in wpairs: w = wpairs[(e[0],node)]
            else : w = wpairs[(node,e[0])]
            sum0 += w
            if (e[1],node) in wpairs: w = wpairs[(e[1],node)]
            else : w = wpairs[(node,e[1])]
            sum1 += w
    if sum0 < sum1 : return e[0]
    else : return e[1] 

# Creating affiliation for each individual; as identified by groups
def affiliation(cur,group,iItem,iIssue,iAddress):
    '''This function takes in a set of author_ids that are deemed to the same
       individual and returns a dict year_aff[<year>]=<preffered name>
       It uses the Djikstra's shortest path algorithm to minimize the number 
       of transfers for the individual. 
    '''
    year_dict = dict()
    year_taken = set()
    # Building year_dict
    for author in group:
        year = iIssue[author].year
        if not isinstance(year, int): continue       
        add = iAddress[author].fullAdd.lower()
        if len(add) > 1 and add[-4:] == ' USA':
            city, state, pin = sm.usAddress(add)
            org_name = add.split(',')[0].strip()
            cur.execute("SELECT pref_name from Org_Class_CS WHERE org_name=(%s) AND state=(%s) AND city=(%s);",(org_name,state,city))
            for i in xrange(cur.rowcount):
                pref_name=cur.fetchone()[0]
                if year in year_taken: year_dict[year].append(pref_name)
                else :
                    year_dict[year]=[pref_name]
                    year_taken.add(year)
        elif year not in year_taken and year in year_dict: \
            year_dict[year].extend(list(iItem[author].pref_name))
        elif year not in year_taken and year not in year_dict : \
            year_dict[year] = list(iItem[author].pref_name)

    # If no year is present, return year 0 and '_' as pref_name
    # This is a data anomaly
    if len(year_dict.keys()) == 0:
         return {0:"_"}
        
    # If only one year is present, return that year and the most common prefname 
    if len(year_dict.keys()) == 1: 
         y = year_dict.keys()[0]
         pref_name = Counter(year_dict[y]).most_common(1)[0][0]
         return {y:pref_name}


    years = year_dict.keys()
    years.sort()
    for i in xrange(len(years)-2):
        year_dict[years[i]].extend(list(set(year_dict[years[i+1]])))
        year_dict[years[i]].extend(list(set(year_dict[years[i+2]])))
   
    year_dict[years[-2]].extend(list(set(year_dict[years[-1]])))

    for y in years: year_dict[y] = Counter(year_dict[y])

    # Else build graph for using Dijkstra's shortest path algo
    G = dict()
    start, end = 's','t'
    first_set, last_set = year_dict[years[0]].keys(), year_dict[years[-1]].keys()
    G[start], G[end] = dict(), dict()
    for pref_name in first_set: G[start][(years[0],pref_name)] = \
                                1.0/year_dict[years[0]][pref_name]
    for pref_name in last_set: G[(years[-1],pref_name)] = {end:0}
    for i in xrange(len(years)-1):
        #c_y:cur_year, n_y:next_year 
        c_y, n_y = years[i], years[i+1]
        #c_s:cur_set, n_s:next_set
        c_s, n_s = year_dict[c_y].keys(), year_dict[n_y].keys()
        #c_p:cur_pref_name, n_p:next_pref_name
        for c_p in c_s:
            G[(c_y,c_p)] = dict()
            for n_p in n_s:
                if c_p == n_p: G[(c_y,c_p)][(n_y,n_p)] = 0     
                else: G[(c_y,c_p)][(n_y,n_p)] = 1.0/year_dict[n_y][n_p]

    # Implement Dijkstra's algo to find shortest path from start to end
    inf = float('inf')
    def relax(W,u,v,D,P):
        """Helper function for dijkstra's algo
        """
        d = D.get(u,inf) + W[u][v]
        if d < D.get(v,inf):
            D[v], P[v] = d, u
            return True
        else: return False

    def dijkstra(G,s):
        """ Dijkstra's algo using heaps
        """
        D, P, Q, S = {s:0}, {}, [(0,s)], set()
        while Q:
            _, u = heappop(Q)
            if u in S: continue
            S.add(u)
            for v in G[u]:
                relax(G,u,v,D,P)
                heappush(Q,(D[v],v))
        return D, P

    # Use Dijkstra's algo
    D, P = dijkstra(G,start)
    year_aff = dict()
    node = P[end]
    while not node == start:
        year_aff[node[0]] = node[1] 
        node = P[node]
    return year_aff

def individual(cur,group,affiliation,first,init2,name_hash):
    '''Populates the following tables: Individual, Individual_Author and
       Individual_Affiliation
    '''
    last = name_hash[:-2]
    init1 = name_hash[-1]
    group = tuple(group)

    # Field of individual is the maximum occuring field.
    # If no field exists, then coloumn is left blank.
    i_field = ''
    try:
        cur.execute("SELECT subject_cat FROM Author_Subject WHERE author_id IN %s;",(group,))
    except Exception, e: 
        print psycopg2.errorcodes.lookup(e.pgcode[:2])
        print psycopg2.errorcodes.lookup(e.pgcode)
    if cur.rowcount > 0:
        field_candidates = list()
        for f in cur.fetchall():
            field_candidates.append(f[0])     
        i_field = Counter(field_candidates).most_common(1)[0][0]
    query = ''
    try:
        query = cur.mogrify('''INSERT INTO Individual (name_hash,first_name,first_initial,
                     second_initial, last_name, individual_field) VALUES (%s,%s,%s,%s,%s,%s)
                      RETURNING (individual_id);''',(name_hash,first,init1,init2,last,i_field))
        cur.execute(query)
        id = int(cur.fetchone()[0])
    except Exception, e: 
        print query
        print e.pgerror

    for author in group:
        try:
            cur.execute("INSERT INTO Individual_Author VALUES (%s,%s);"\
                        ,(id,author))
        except Exception, e:
            print psycopg2.errorcodes.lookup(e.pgcode[:2])
            print psycopg2.errorcodes.lookup(e.pgcode)


    start = min(affiliation.keys())
    current = affiliation[start]
    end = -1
    for y in sorted(affiliation.keys()):
        if not affiliation[y] == current:
            end = y
            stmt = "INSERT INTO Individual_Affiliation VALUES (%s,%s,%s,'%s');"%(id,start,end,current)
            try:
                cur.execute(stmt)
            except Exception, e: 
                print 'Error executing:', stmt
                print psycopg2.errorcodes.lookup(e.pgcode[:2])
                print psycopg2.errorcodes.lookup(e.pgcode)
            current = affiliation[y]
            start = y
    end = max(affiliation.keys())
    if isdigit(start) and isdigit(end):
        stmt = "INSERT INTO Individual_Affiliation VALUES (%s,%s,%s,'%s');"%(id,start,end,current)
        try: 
            cur.execute(stmt)
        except Exception, e: 
            print 'Error executing:', stmt
            print psycopg2.errorcodes.lookup(e.pgcode[:2])
            print psycopg2.errorcodes.lookup(e.pgcode)

def disambiguate(aName):
    ''' This function accepts a <name hash> and using the fast community detection algorithm creates groups of names
        that are likely to be the same author. It then either enters them in the database or writes their info to files
        for verification
    '''

    def return_handle(cur, aNamePrint, code):
        '''This function takes care of cleaning files before returning the disambiguate function
           code: 0 - remove all files
                 1 - remove .debug and .wpairs files
                 2 - remove .debug file
        '''
        #Remove .groups and .wpairs file
        try:
            ### Debug ###
            if code in [0,1,2]: os.remove('%s.debug'%aNamePrint)
            ### End Debug ###
            if code in [0,1]: os.remove('%s.wpairs'%aNamePrint) 
            if code == 0: os.remove(group_file)
        except OSError as e:
            print e.errno, e.filename, e.strerror 
            pass
        conn.commit()
        cur.close()
        conn.close()

    # aName contains space. E.g. 'adams j'. This is how names are stored in the databse
    # aNamePrint is the stripped version that contains only alpha-num chars. 'adamsj'
    aNamePrint = aName[:-2]+aName[-1]
    patt = re.compile('[\W_]+')
    aNamePrint = patt.sub('',aNamePrint)

    ### For Debugging ###
    open("%s.debug"%aNamePrint,'a').close()
    ### End Debug ###

    itemA = dict()
    conn=psycopg2.connect(database="PubData",port=5433)
    cur = conn.cursor()
    cur.execute("SELECT B.author_id, A.item_id FROM Item_author A INNER JOIN Author_Hash B ON A.author_id=B.author_id WHERE name_hash=(%s);",(aName,))
    #print 'No. of Author names:', cur.rowcount
    bucket_size = cur.rowcount
    for row in cur.fetchall(): itemA[row[0]]=row[1]
    
    # Fetching information about the authors and storing them in data structures
    iAuthor, iAddress, iItem, iIssue, iCoAuthor = dict(), dict(), dict(), dict(), dict()
    for author in itemA.keys():
        # Information related to the author
        data = list()
        cur.execute("SELECT init2,suffix,first_name FROM Author_Hash A INNER JOIN Author_Name B ON A.author_id=B.author_id WHERE A.author_id=(%s);",(author,))
        if cur.rowcount == 0 : data = [' ',' ',' ']
        else:
            temp = cur.fetchone()
            for i in temp:
                if i is None: data.append(' ')
                else: data.append(i)
        # Extract second initial from fullname
        cur.execute("SELECT fullname FROM Author WHERE author_id=(%s);",(author,))
        if cur.rowcount == 0 : "Author %s does not show up. This should not be happening."
        else: 
            fullname = cur.fetchone()[0]
            initials = fullname.split(',')[1].strip()
            if len(initials) > 1:
                data[0] = initials[1].lower()
        # Author keywords
        cur.execute("SELECT author_keyword FROM Author_Keyword WHERE author_id=(%s);",(author,))
        keywords = set()
        if cur.rowcount > 0 :
            for t in cur.fetchall() : keywords.add(t[0])
        ai = sm.AuthorInfo(data[0],data[1],data[2],keywords)
        iAuthor[author] = ai

        # Information related to the Address
        cur.execute("SELECT full_address,email FROM Author_Address A INNER JOIN Address B ON A.address_id = B.address_id WHERE A.author_id=(%s);",(author,))
        if cur.rowcount == 0 : data = [' ',' ']
        else:
            temp = cur.fetchone()
            data = list()
            for i in temp:
                if i is None: data.append(' ')
                else: data.append(i)
        ai = sm.AddressInfo(data[0],data[1])
        iAddress[author] = ai
        
        # Information related to Item
        data = range(5)
        cur.execute("SELECT title FROM Item WHERE item_id=(%s);",(itemA[author],))
        if cur.rowcount == 0: data[0] = ' '
        else : data[0] = cur.fetchone()[0]
        cur.execute("SELECT language FROM Item_Language WHERE item_id=(%s);",(itemA[author],))
        if cur.rowcount == 0: data[1] = set()
        else : 
            tset = set()
            for x in cur.fetchall() : tset.add(x[0])
            data[1] = tset
        cur.execute("SELECT item_keyword FROM Item_Keyword WHERE item_id=(%s);",(itemA[author],))
        if cur.rowcount == 0: data[2] = set()
        else :
            tset = set()
            for x in cur.fetchall():tset.add(x[0])
            data[2] = tset
        cur.execute("SELECT B.org_name FROM Research_org A INNER JOIN Organization B ON A.org_id = B.org_id WHERE A.item_id=(%s);",(itemA[author],))
        if cur.rowcount == 0: data[3] = set()
        else :
            tset = set()
            for x in cur.fetchall() : tset.add(x[0])
            data[3] = tset
        cur.execute("SELECT pref_name FROM Item_PrefName WHERE item_id=(%s);",(itemA[author],))
        if cur.rowcount == 0 : data[4] = set()
        else :
            tset = set()
            for x in cur.fetchall() : tset.add(x[0])
            data[4] = tset

        ii = sm.ItemInfo(data[0],data[1],data[2],data[3],data[4])
        iItem[author] = ii     

        # Information about Issue
        cur.execute('''SELECT D.full_title, D.subject, D.year FROM Item A INNER JOIN 
                       (SELECT B.issue_id, B.full_title, C.subject, B.year  FROM 
                       Issue B INNER JOIN Subject_Cat C ON B.issue_id=C.issue_id) 
                       AS D ON A.issue_id=D.issue_id WHERE item_id=(%s);''',(itemA[author],))
        data = range(3)
        if cur.rowcount == 0: data = [' ',set(),' '] 
        else : 
            tset = set()
            temp = cur.fetchone()
            data[0] = temp[0]
            tset.add(temp[1])
            data[2] = int(temp[2])
            for x in cur.fetchall(): tset.add(x[1])
            data[1] = tset
        iIssue[author] = sm.IssueInfo(data[0],data[1],data[2])

        # Information about CoAuthors
        tset = set()
        cur.execute('''SELECT name_hash FROM
                       Item_Author A INNER JOIN Author_Hash B
                       ON A.author_id=B.author_id
                       WHERE A.item_id=(%s)
                       AND NOT A.author_id=(%s);''',(itemA[author],author))    
        if cur.rowcount > 0:
            for x in cur.fetchall() : tset.add(x[0])
        tset.discard(aName)
        iCoAuthor[author] = sm.CoAuthorInfo(tset)

#    for key in itemA.keys(): 
#        print key, iIssue[key].title
#        print iIssue[key].subject
    

    # Compute edge scores
    if bucket_size > 1000 :
        x = (bucket_size - 1000.0)/1000.0
        a, b = 7.0/552, 79.0/552 
        cutoff = ceil(a*x*x + b*x + 5)
    elif bucket_size <= 20:
        cutoff = 3
    elif bucket_size <= 100:
        cutoff = 4
    else:
        cutoff = 5
    #print '%s cutoff = %d'%(aNamePrint,cutoff)
    edges_exist = False
    wpairs = dict()
    cite_set = set() # Stores pair of authors with citation between them
    coauthor_set = set() # Stores pair of authors that share coauthors with same last name first initial
    negative = list() # Stores negative edges
    # singles contain nodes not present in the graph
    singles = set(itemA.keys())
    for a in comb(itemA.keys(),2):
        au_score = sm.authorScore(iAuthor[a[0]],iAuthor[a[1]])
        ad_score = sm.addressScore(iAddress[a[0]],iAddress[a[1]])
        it_score = sm.itemScore(iItem[a[0]],iItem[a[1]])
        is_score = sm.issueScore(iIssue[a[0]],iIssue[a[1]])
        co_score = sm.coAuthorScore(iCoAuthor[a[0]],iCoAuthor[a[1]])
        if co_score > 0 : coauthor_set.add((a[0],a[1]))
        ci_score = sm.citeScore(itemA[a[0]],itemA[a[1]],cur)
        if ci_score > 0 : cite_set.add((a[0],a[1]))
        in_score = sm.interaction(iItem[a[0]],iItem[a[1]],iIssue[a[0]],iIssue[a[1]],iCoAuthor[a[0]],iCoAuthor[a[1]])
        score = au_score + ad_score + it_score + is_score + co_score + ci_score + in_score
        # Change : subtracting cutoff from edge weight
        wpairs[(a[0],a[1])] = score - cutoff
        if score < 0 : negative.append([a[0],a[1]])
        if score > cutoff : 
            singles.difference_update([a[0],a[1]])
            edges_exist = True

    # If no edge exists, skip rest of disambiguate function
    # and call individual()
    if not edges_exist:
        for author in singles:
            au = iAuthor[author]
            f, s = name(au)
            aff = {iIssue[author].year:iItem[author].pref_name.pop()}
            grp = set([author])
            individual(cur,grp,aff,f,s,aName)

        # Insert completed hashes in Hash_Done
        cur.execute("INSERT INTO Hash_Done (name_hash) VALUES (%s);",(aName,))            
        return_handle(cur,aNamePrint,2) 
        return
        # disambiguate() ends

    # Map node ids to sequential numbers. Helps increase computation speed immensely
    # Also write new edge file to be used by fast community algorithm
    i = 1
    f = open('%s.wpairs'%aNamePrint,'w')
    nodemap = dict()
    for e in wpairs.keys():
        if wpairs[e] > 0 :
            n1,n2,w = e[0],e[1],wpairs[e]
            if n1 in nodemap : n1 = nodemap[n1]
            else : 
                nodemap[n1] = i
                n1 = i
                i += 1
            if n2 in nodemap : n2 = nodemap[n2]
            else : 
                nodemap[n2] = i
                n2 = i
                i += 1
            f.write('%d\t%d\t%d\n'%(n1,n2,w))
    f.close() # Edge file written

    # Reverse mapping dictionary
    revmap = dict()
    for k in nodemap.keys() : revmap[nodemap[k]] = k

    # Running fast community algorithm
    command = "sudo /media/RaidDisk1/disamb/fast_comm/FastCommunity_wMH -f %s.wpairs -l 1"%aNamePrint
    try:
        p = subprocess.Popen(command,shell=True)
        p.wait() # Waiting for algorithm to finish
    except OSError as e:
        print e.strerror 
        print 'except', aNamePrint
        return_handle(cur, aNamePrint, 1)
        return

    # Reading group file written by fast_community algorithm
    group_file = '%s-fc_1.groups'%aNamePrint
    gs, groups = list(),list()
    g = set()
    gdict= dict()
    code = -1 #Code used to remove files at the end
    try:
        # Opening group file
        gfile = open(group_file,'r')
    except:
        # Groups file does not exist
        # Perform simple grouping based on connected components
        simple_cutoff = 10 - cutoff
        G = dict()
        for e in wpairs.keys():
            n1, n2, w = e[0], e[1], wpairs[e]
            if not n1 in G : G[n1] = set()
            if not n2 in G : G[n2] = set()
            if w > simple_cutoff:
                G[n1].add(n2)
                G[n2].add(n1)
        gs = components(G)
        code = 1        
    else:
        # Groups file exists
        for line in gfile.readlines():
            if line[:5] == 'GROUP' :
                if len(g) > 0 : gs.append(g)
                g = set()
            else :
                node = revmap[int(line.split()[0])] 
                g.add(node)
        gs.append(g)
        gfile.close()
        code = 0

    # Generic group handling begins
    counter = 0
    for g in gs:
        if len(g) == 1: singles.update(g)
        else: 
            new_g = set()
            for node in g:
                gdict[node] = counter
                new_g.add(node)
            groups.append(new_g)
            counter += 1 
            
    # Assigning group numbers to singletons
    for node in singles:
        if not node in gdict:
            counter += 1
            gdict[node] = counter

#---Removing negative edge weights from within a group
    for e in negative:
        if gdict[e[0]] == gdict[e[1]]:
            group_no = gdict[e[0]]
            rnode = removeNode(e,groups[group_no],wpairs)
            groups[group_no].discard(rnode)
            singles.add(rnode)
            counter += 1
            gdict[rnode] = counter

#---Post clustering group merge
    iGroup = list()
    # Create group info for pairwise comparison
    for i in xrange(len(groups)):
        f_name, s_init = list(), list() #First Name and Second initial
        address = set()
        for author in groups[i]:
            # Name
            au = iAuthor[author]
            f, s = name(au)
            if not f == '': f_name.append(f)
            if not s == '':s_init.append(s)
            # Address    
            ad = iAddress[author]
            if ad.fullAdd[-4:] == 'USA': 
                c,s,p = sm.usAddress(ad.fullAddress.lower())
                address.add((c,s))
        if len(f_name) == 0: first = ''
        else : first = Counter(f_name).most_common(1)[0][0]
        if len(s_init) == 0: init2 = ''
        else : init2 = Counter(s_init).most_common(1)[0][0]
        aff = affiliation(cur,groups[i],iItem,iIssue,iAddress)
        ginfo = sm.GroupInfo(i,(first,init2),address,aff)
        iGroup.append(ginfo)

    # Create graph to merge connected components
    G = dict() # Adjacency list
    for i in xrange(len(groups)): G[i] = set()
    for g in comb(iGroup,2):
        # Group Number
        i1, i2 = g[0].i, g[1].i
        # Name
        name_score, addr_score, cite_score, co_score, aff_score = 0,0,0,0,0
        f1, s1 = g[0].name
        f2, s2 = g[1].name
        if f1 == '' or f2 == '' : pass
        elif f1 == f2 : name_score += 5
        else : continue
        if s1 == '' or s2 == '' : pass
        elif s1 == s2 : name_score += 5
        else : continue
        if name_score < 10 : name_score = 0 
        # Address
        if len(g[0].address & g[1].address) > 0 : addr_score = 10
        # Citation and CoAuthor
        cite_found, coauthor_found = False, False 
        for x,y in prod(groups[i1], groups[i2]):
            if (x,y) in cite_set or (y,x) in cite_set:
                cite_found = True
                cite_score = 10
                if coauthor_found: break
            if (x,y) in coauthor_set or (y,x) in coauthor_set:
                coauthor_found = True
                co_score = 10
                if cite_found: break        
        # Affiliation
        aff1, aff2 = g[0].affiliation, g[1].affiliation
        for y in aff1.keys():
            if aff1[y] == aff2.get(y,'NIL'):
                aff_score = 10
                break
        score = name_score+addr_score+cite_score+co_score+aff_score
        #print 'Groups', i1, i2
        #print 'Name:', name_score, 'Address:', addr_score, 'Cite:', cite_score, \
        #      'CoAuthor:', co_score, 'Affiliation:', aff_score, 'Total:', score
        if score >= 20:
            G[i1].add(i2)
            G[i2].add(i1)

    # Forming new, possibly merged, groups 
    group_list = components(G)
    #print 'group_list:', group_list
    new_groups = list()
    for gl in group_list:
        g = set()
        for x in gl: g.update(groups[x])
        new_groups.append(g)

    '''        
#############################################################
# Printing group information for manual curation
    #Add the singles group to the end
    new_groups.append(singles)
    # Make directory for author hash and store groups inside
    os.mkdir(aNamePrint)
    i = 0
    for group in new_groups:
        file = ''
        file = open("%s/Group%s.txt"%(aNamePrint,i),'w')
        i += 1
        file.write("Author_id\tSec Initial\tSuffix\tFirst\tKeywords\tCo Authors\tAddress\tEmail\tItem Title\tLanguage\tItem Keywords\tOrganizations\tPref Names\tYear\tIssue Title\tIssue Subjects \n")
        for author in group:
            au = iAuthor[author]
            ad = iAddress[author]
            it = iItem[author]
            iu = iIssue[author]
            co = iCoAuthor[author]
            keywords = ', '.join(au.keywords)
            au_string = " %s\t%s\t%s\t%s"%(au.init2,au.suffix,au.first,keywords)
            ad_string = " %s\t%s"%(ad.fullAdd,ad.email)
            language = ', '.join(it.lang)
            keywords = ', '.join(it.keywords)
            org = ', '.join(it.org)
            pref_name = ', '.join(it.pref_name)
            it_string = " %s\t%s\t%s\t%s\t%s"%(it.title,language,keywords,org,pref_name)
            subject = ', '.join(iu.subject)
            iu_string = " %s\t%s\t%s"%(iu.year,iu.title,subject)
            co_string = ', '.join(co.authors)
            file.write("%d\t%s\t%s\t%s\t%s\t%s\n"%(author,au_string,co_string,ad_string,it_string,iu_string))
        file.close()

#############################################################

    '''
#---Populate Individual details using individual function
    for ng in new_groups:
        f_name, s_init = list(), list() #First Name and Second initial
        for author in ng:
            # Name
            au = iAuthor[author]
            f, s = name(au)
            if not f == '': f_name.append(f)
            if not s == '': s_init.append(s)
        if len(f_name) == 0: first = ''
        else : first = Counter(f_name).most_common(1)[0][0]
        if len(s_init) == 0: init2 = ''
        else : init2 = Counter(s_init).most_common(1)[0][0]
        aff = affiliation(cur,ng,iItem,iIssue,iAddress)
        #print ' '.join(['%d:%s'%(y,aff[y])for y in sorted(aff.keys())]) 

        individual(cur,ng,aff,first,init2,aName)

    for author in singles:
        au = iAuthor[author]
        f, s = name(au)
        aff = {iIssue[author].year:iItem[author].pref_name.pop()}
        grp = set([author])
        individual(cur,grp,aff,f,s,aName)

    # Insert completed hashes in Hash_Done
    cur.execute("INSERT INTO Hash_Done (name_hash) VALUES (%s);",(aName,))                
    return_handle(cur,aNamePrint,code)

