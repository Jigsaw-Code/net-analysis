This directory contains files mapping Autonmous Systems (AS) to
the their Organizations (Org).

     http://www.caida.org/research/topology/as2org/
     http://www.caida.org/data/as-organizations/


The as2org files contain two different types of entries: AS numbers and
organizations.  The two data types are divided by lines that start with
'# format....'. An example can be found below.

# format: aut|changed|name|org_id|source
1|20120224|LVLT-1|LVLT-ARIN|ARIN
# format: org_id|changed|name|country|source
LVLT-ARIN|20120130|Level 3 Communications, Inc.|US|ARIN

----------
AS fields
----------
aut     : the AS number
changed : the changed date provided by its WHOIS entry
name    : the name provide for the individual AS number
org_id  : maps to an organization entry
source  : the RIR or NIR database which was contained this entry

--------------------
Organization fields
--------------------
org_id  : unique ID for the given organization
           some will be created by the WHOIS entry and others will be
           created by our scripts
changed : the changed date provided by its WHOIS entry
name    : name could be selected from the AUT entry tied to the
           organization, the AUT entry with the largest customer cone,
          listed for the organization (if there existed an stand alone
           organization), or a human maintained file.
country : some WHOIS provide as a individual field. In other cases
           we inferred it from the addresses
source  : the RIR or NIR database which was contained this entry

------------------------
Acceptable Use Agreement
------------------------

the AUA that you accepted when you were given access to these datas is
included in pdf format as a separate file in the same directory as this
README file.  When referencing this data (as required by the AUA),
please use:

     The CAIDA AS Organizations Dataset, <date range used>
     http://www.caida.org/data/as-organizations

Also, please, report your publication to CAIDA
(http://www.caida.org/data/publications/report-publication.xml).
