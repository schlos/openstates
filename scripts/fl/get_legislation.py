#!/usr/bin/env python
import urllib2
import re
import datetime as dt
from BeautifulSoup import BeautifulSoup

# ugly hack
import sys
sys.path.append('./scripts')
from pyutils.legislation import LegislationScraper, NoDataForYear

class FLLegislationScraper(LegislationScraper):

    state = 'fl'

    def scrape_session(self, chamber, year, special=''):
        if chamber == 'upper':
            chamber_name = 'Senate'
            bill_abbr = 'S'
        elif chamber == 'lower':
            chamber_name = 'House'
            bill_abbr = 'H'

        # Base url for bills sorted by first letter of title
        base_url = 'http://www.flsenate.gov/Session/index.cfm?Mode=Bills&BI_Mode=ViewBySubject&Letter=%s&Year=%s&Chamber=%s'
        session = year + special

        # Bill ID format
        bill_re = re.compile("%s (\d{4}%s)" % (bill_abbr, special))
    
        # Go through all sorted bill list pages
        for letter in "ABCDEFGHIJKLMNOPQRSTUVWXYZ":
            bill_list_url = base_url % (letter, session, chamber_name)
            print bill_list_url
            bill_list = BeautifulSoup(urllib2.urlopen(bill_list_url).read())
            
            # Bill ID's are bold
            for b in bill_list.findAll('b'):
                if not b.string:
                    continue
            
                match = bill_re.search(b.string)
                if match:
                    # Bill ID and number
                    bill_id = match.group(0)
                    bill_number = match.group(1)

                    # Get bill name and info url
                    bill_link = b.parent.findNext('td').a
                    bill_name = bill_link.string.strip()
                    info_url = "http://www.flsenate.gov/Session/%s&Year=%s" % (bill_link['href'], year)
                    print "Getting %s: %s" % (bill_id, bill_name)

                    # Add bill
                    self.add_bill(chamber, session, bill_id, bill_name)

                    # Get bill info page
                    info_page = BeautifulSoup(urllib2.urlopen(info_url).read())

                    # Get all bill versions
                    bill_table = info_page.find('a', attrs={'name':'BillText'}).parent.parent.findNext('tr').td.table
                    for tr in bill_table.findAll('tr')[1:]:
                        version_name = tr.td.string
                        version_url = "http://www.flsenate.gov%s" % tr.a['href']
                        self.add_bill_version(chamber, session, bill_id,
                                              version_name, version_url)

                    # Get actions
                    act_table = info_page.find('pre', "billhistory")
                    act_str = ""
                    for line in act_table.findAll(text=True):
                        act_str += line + "\n"
                    act_str = act_str.replace('&nbsp;', ' ')
                    act_re = re.compile('^  (\d\d/\d\d/\d\d) (SENATE|HOUSE) (.*\n(\s{16,16}.*\n){0,})', re.MULTILINE)
                    for act_match in act_re.finditer(act_str):
                        action = act_match.group(3).replace('\n', ' ')
                        action = re.sub('\s+', ' ', action)
                        if act_match.group(2) == 'SENATE':
                            act_chamber = 'upper'
                        else:
                            act_chamber = 'lower'
                        self.add_action(chamber, session, bill_id,
                                        act_chamber, action,
                                        act_match.group(1))

    def scrape_bills(self, chamber, year):
        # Data available for 1998 on
        if int(year) < 1998 or int(year) > dt.date.today().year:
            raise NoDataForYear(year)

        # These are all the session types that I've seen
        for session in ['', 'A', 'B', 'C', 'D', 'O']:
            self.scrape_session(chamber, year, session)

if __name__ == '__main__':
    FLLegislationScraper().run()
