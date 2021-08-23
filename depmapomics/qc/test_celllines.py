import re
from gsheets.api import Sheets
import numpy as np
import pandas as pd
import pytest
from depmapomics.qc.test_compare_to_ref_release import get_both_release_lists_from_taiga
from depmapomics.qc.config import (LEGACY_PATCH_FLAGS, LINES_TO_RELEASE, LINES_TO_DROP, PORTAL,
                                   PREV_RELEASE, NEW_RELEASE, FILE_ATTRIBUTES)
from taigapy import TaigaClient
tc = TaigaClient()

####### FIXTURES ####
def tsv2csv(df):
    df.to_csv('/tmp/data.tsv', index=False)
    df = pd.read_csv('/tmp/data.tsv', sep='\t')
    return df


@pytest.fixture(scope='module')
def arxspans(request):
    return get_both_release_lists_from_taiga(request.param)


PARAMS_unexpected_arxspans = [(x['file'], x['omicssource']) for x in FILE_ATTRIBUTES]
@pytest.mark.parametrize('arxspans, omicssource', PARAMS_unexpected_arxspans, indirect=['arxspans'])
@pytest.mark.parametrize('portal', [PORTAL])
@pytest.mark.bookkeeping
def test_unexpected_arxspans(arxspans, omicssource, portal):
    arxspans1, arxspans2 = arxspans

    # TODO create option for each portal
    if portal == 'all':
        lines_to_release = set(LINES_TO_RELEASE.stack())
    elif portal == 'ibm':
        lines_to_release = set(LINES_TO_RELEASE['ibm'].dropna()) | set(LINES_TO_RELEASE['dmc'].dropna())
    else:
        lines_to_release = set(LINES_TO_RELEASE[portal].dropna())

    dropped_lines = arxspans1 - arxspans2
    added_lines = arxspans2 - arxspans1

    unexpected_added_lines = added_lines - lines_to_release
    lines_to_drop = LINES_TO_DROP[omicssource]
    unexpected_dropped_lines = dropped_lines - lines_to_drop
    failed_to_drop = lines_to_drop & arxspans2
    failed_to_release = lines_to_release - arxspans2

    assert (not unexpected_added_lines) & (not unexpected_dropped_lines) & (not failed_to_drop) & (not failed_to_release), \
                '\nunexpected added lines: {}\nunexpected dropped lines: {}\nfailed to drop: {}\nfailed to release: {}\n'.format(
                    unexpected_added_lines, unexpected_dropped_lines, failed_to_drop, failed_to_release)

    # TODO: write a test to make sure data from the same omics source is shared across the files

    # TODO: write a test that checks 'failed_to_release' based on omicssource