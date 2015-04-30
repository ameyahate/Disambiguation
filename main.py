# This file call the disambiguate function with appropriate name hash
from disambiguate import disambiguate
import psycopg2
import random
import multiprocessing
import sys

if __name__ == '__main__':
        
    # Eshtablish connection with database
    conn=psycopg2.connect(database="PubData",
                          port=5433)
    cur = conn.cursor()
    cur.execute("SELECT name_hash FROM Hash_List A WHERE NOT EXISTS\
                 (SELECT 1 FROM Hash_Done WHERE name_hash=A.name_hash);")
    print 'Total: ', cur.rowcount
    sys.stdout.flush()
    hashes = [t[0] for t in cur.fetchall()] 
    cur.close()
    conn.close()

    remove_set = set(['zu castell w','soroka .'])
    hashes = [x for x in hashes if x not in remove_set]
    print 'Final total: ', len(hashes)
       
    pll = 32
    for i in xrange(len(hashes)/pll + 1):
        procs = []
        for h in hashes[i*pll:min((i+1)*pll,len(hashes))]:
            p = multiprocessing.Process(target=disambiguate, args=(h,))
            p.daemon = True
            procs.append(p)
            p.start()
        for p in procs: p.join()
