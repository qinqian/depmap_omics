from genepy import terra
from genepy.utils import helper as h
from genepy import mutations as mut
import os
import dalmatian as dm
import pandas as pd
from genepy.google.gcp import cpFiles
import numpy as np
from genepy.mutations import filterAllelicFraction, filterCoverage
from collections import Counter
from depmapomics import tracker as track
from depmapomics import utils
from depmapomics.config import TMP_PATH, ENSEMBL_SERVER_V, Mutationsreadme
import dalmatian as dm
import pandas as pd
from taigapy import TaigaClient
tc = TaigaClient()
from gsheets import Sheets


def download_maf_from_workspace(refwm, sample_set_ids=['all_ice', 'all_agilent'],
                                output_maf='/tmp/mutation_filtered_terra_merged.txt'):
  sample_sets = refwm.get_sample_sets()
  dfs = []
  for sample_set_id in sample_sets.index.intersection(sample_set_ids):
    cpFiles(sample_sets.loc[sample_set_id, 'filtered_CGA_MAF_aggregated'],
                '/tmp/tmp.txt', payer_project_id='broad-firecloud-ccle', verbose=False)
    df = pd.read_csv('/tmp/tmp.txt', sep='\t', low_memory=False)
    dfs.append(df)
  dfs_concat = pd.concat(dfs)
  dfs_concat.to_csv(output_maf, index=False, sep='\t')
  return dfs_concat


def removeDuplicates(a, loc, prepended=['dm', 'ibm', 'ccle']):
  """
  This function is used to subset a df to only the columns with the most up to date names

  We consider a naming convention preprended_NAME_version and transform it into NAME with latest NAMES

  Args:
  ----
    a: the dataframe where loc contain the names
    loc: the location of names
    prepended: the set of possible prepended values

  Returns:
  -------
    a: the subsetted dataframe
  """
  values = []
  if len(prepended) > 0:
    for i in a[loc]:
      i = i.split('_')
      if i[0] in prepended:
        values.append('_'.join(i[1:]))
      else:
        values.append('_'.join(i))
      if i[-1] == '2':
        print(i)
    a[loc] = values
  a = a.sort_values(by=[loc])
  todrop = []
  for i in range(len(a[loc]) - 1):
    e = a[loc][i + 1].split('_')
    if len(e[-1]) == 1:
      if int(e[-1]) > 1 and e[0] == a[loc][i].split('_')[0]:
        todrop.append(a[loc][i])
        print(a[loc][i])
        print(e)
  a = a.set_index(loc).drop(todrop).reset_index()
  return a


def annotateLikelyImmortalized(maf, sample_col="DepMap_ID",
                               genome_change_col="Genome_Change", TCGAlocs=['TCGAhsCnt', 'COSMIChsCnt'],
                               max_recurrence=0.05, min_tcga_true_cancer=5):
  maf['is_likely_immortalization'] = False
  leng = len(set(maf[sample_col]))
  tocheck = []
  for k, v in Counter(maf[genome_change_col].tolist()).items():
    if v > max_recurrence*leng:
      tocheck.append(k)
  for val in list(set(tocheck)-set([np.nan])):
    if np.nan_to_num(maf[maf[genome_change_col] == val][TCGAlocs], 0).max() < min_tcga_true_cancer:
      maf.loc[maf[maf[genome_change_col]
                  == val].index, 'is_likely_immortalization'] = True
  return maf


def addAnnotation(maf, NCBI_Build='37', Strand="+"):
  """
  adds NCBI_Build and Strand annotaation on the whole maf file
  """
  maf['NCBI_Build'] = NCBI_Build
  maf['Strand'] = Strand
  return maf


def add_variant_annotation_column(maf):
    mutation_groups={
        "other conserving": ["5'Flank", "Intron", "IGR", "3'UTR", "5'UTR"],
        "other non-conserving":["In_Frame_Del", "In_Frame_Ins", "Stop_Codon_Del",
            "Stop_Codon_Ins", "Missense_Mutation", "Nonstop_Mutation"],
        'silent': ['Silent'],
        "damaging":['De_novo_Start_OutOfFrame','Frame_Shift_Del','Frame_Shift_Ins',
            'Splice_Site', 'Start_Codon_Del', 'Start_Codon_Ins', 'Start_Codon_SNP','Nonsense_Mutation']
    }

    rename = {}
    for k,v in mutation_groups.items():
      for e in v:
        rename[e] = k
    maf['Variant_annotation'] = [rename[i] for i in maf['Variant_Classification'].tolist()]
    return maf

def postprocess_mutations_filtered_wes(refworkspace, sample_set_name = 'all',
                                       output_file='/tmp/wes_somatic_mutations.csv'):
  refwm = dm.WorkspaceManager(refworkspace).disable_hound()
  filtered = refwm.get_sample_sets().loc[sample_set_name]['filtered_CGA_MAF_aggregated']
  print('copying aggregated filtered mutation file')
  cpFiles([filtered], "/tmp/mutation_filtered_terra_merged.txt")
  print('reading the mutation file')
  mutations = pd.read_csv('/tmp/mutation_filtered_terra_merged.txt', sep='\t', low_memory=False)
  mutations = mutations.rename(columns={"i_ExAC_AF":"ExAC_AF",
                                        "Tumor_Sample_Barcode":'DepMap_ID',
                                        "Tumor_Seq_Allele2":"Tumor_Allele"}).\
  drop(columns=['Center','Tumor_Seq_Allele1'])
  # mutations = annotate_likely_immortalized(mutations, TCGAlocs = ['TCGAhsCnt', 'COSMIChsCnt'], max_recurrence=0.05, min_tcga_true_cancer=5)
  print('writing CGA_WES_AC column')
  mutations['CGA_WES_AC'] = [str(i[0]) + ':' + str(i[1]) for i in np.nan_to_num(mutations[['t_alt_count','t_ref_count']].values,0).astype(int)]
  # apply version:
  # mutations['CGA_WES_AC'] = mutations[['t_alt_count', 't_ref_count']].fillna(0).astype(int).apply(lambda x: '{:d}:{:d}'.format(*x), raw=True, axis=1)
  print('filtering coverage')
  mutations = filterCoverage(mutations, loc=['CGA_WES_AC'], sep=':', cov=2)
  print('filtering allelic fractions')
  mutations = filterAllelicFraction(mutations, loc=['CGA_WES_AC'], sep=':', frac=0.1)
  print('adding NCBI_Build and strand annotations')
  mutations = addAnnotation(mutations, NCBI_Build='37', Strand="+")
  print('adding the Variant_annotation column')
  mutations = add_variant_annotation_column(mutations)
  print('saving results to output file')
  mutations.to_csv('/tmp/wes_somatic_mutations.csv', index=False)
  return mutations


def managingDuplicates(samples, failed, datatype, tracker):
  # selecting the right arxspan id (latest version)
  renaming = tracker.removeOlderVersions(names=samples,
                                         refsamples=tracker[tracker.datatype == datatype], 
                                         priority="prioritized")

  # reparing QC when we have a better duplicate
  ref = pd.DataFrame(
      tracker[tracker.datatype == datatype]['arxspan_id'])
  replace = 0
  for val in failed:
    if val in list(renaming.keys()):
      a = ref[ref.arxspan_id == ref.loc[val].arxspan_id].index
      for v in a:
        if v not in failed:
          renaming[v] = renaming.pop(val)
          replace += 1
          break
  print('could replace:')
  print(replace)
  return renaming


def postProcess(refworkspace, sampleset='all', mutCol="mut_AC", save_output="", doCleanup=False,  sortby=[
        "DepMap_ID", 'Chromosome', "Start", "End"], todrop=[],
        genechangethresh=0.025, segmentsthresh=2000, ensemblserver=ENSEMBL_SERVER_V,
        rename_cols={"i_ExAC_AF": "ExAC_AF", "Tumor_Sample_Barcode": 'DepMap_ID', 
        "Tumor_Seq_Allele2": "Tumor_Allele"},):
  
  h.createFoldersFor(save_output)
  print('loading from Terra')
  if save_output:
    terra.saveConfigs(refworkspace, save_output + 'config/')
  refwm = dm.WorkspaceManager(refworkspace)
  mutations = pd.read_csv(refwm.get_sample_sets().loc[sampleset, 'filtered_CGA_MAF_aggregated'], sep='\t') 
  mutations = mutations.rename(columns={"i_ExAC_AF": "ExAC_AF", "Tumor_Sample_Barcode": 'DepMap_ID',
                                        "Tumor_Seq_Allele2": "Tumor_Allele"}).drop(columns=['Center', 'Tumor_Seq_Allele1'])

  mutations[mutCol] = [str(i[0]) + ':' + str(i[1]) for i in np.nan_to_num(mutations[
      ['t_alt_count', 't_ref_count']].values, 0).astype(int)]
  mutations = mut.filterCoverage(mutations, loc=[mutCol], sep=':',cov=2)
  mutations = mut.filterAllelicFraction(mutations, loc=[mutCol], sep=':',frac=0.1)
  mutations = addAnnotation(mutations, NCBI_Build='37', Strand="+")
  mutations = annotateLikelyImmortalized(mutations,
                                          TCGAlocs=['TCGAhsCnt', 'COSMIChsCnt'], 
                                          max_recurrence=0.05, min_tcga_true_cancer=5)

  mutations.to_csv(save_output + 'somatic_mutations_all.csv', index=None)
  print('done')
  return mutations

def CCLEPostProcessing(wesrefworkspace, wgsrefworkspace, samplesetname,
                       AllSamplesetName='all', doCleanup=False,
                       my_id='~/.client_secret.json', mystorage_id="~/.storage.json",
                       refsheet_url="https://docs.google.com/spreadshe\
                        ets/d/1Pgb5fIClGnErEqzxpU7qqX6ULpGTDjvzWwDN8XUJKIY",
                       taiga_dataset="cn-latest-d8d4", dataset_description=CNreadme,
                       mutation_groups={
                           "other conserving": ["5'Flank", "Intron", "IGR", "3'UTR", "5'UTR"],
                           "other non-conserving": ["In_Frame_Del", "In_Frame_Ins",
                            "Stop_Codon_Del", "Stop_Codon_Ins", "Missense_Mutation", 
                            "Nonstop_Mutation"],
                           'silent': ['Silent'],
                           "damaging": ['De_novo_Start_OutOfFrame', 'Frame_Shift_Del', 
                            'Frame_Shift_Ins', 'Splice_Site', 'Start_Codon_Del', 'Start_Codon_Ins', 
                            'Start_Codon_SNP', 'Nonsense_Mutation']
                       }, prev=tc.get(name='depmap-a0ab', file='CCLE_mutations'),
                       taiga_dataset="mutations-latest-ed72",
                       **kwargs):

  sheets = Sheets.from_files(my_id, mystorage_id)
  tracker = sheets.get(refsheet_url).sheets[0].to_frame(index_col=0)
  
  wesrefwm = dm.WorkspaceManager(wesrefworkspace)
  wgsrefwm = dm.WorkspaceManager(wgsrefworkspace)  

  if doCleanup:
    #TODO:
    val = ""
    #gcp.rmFiles('gs://fc-secure-012d088c-f039-4d36-bde5-ee9b1b76b912/$val/**/call-tumorMM_Task/*.cleaned.bam')
  # sometimes it does not work so better check again

  # doing wes
  print('doing wes')
  folder=os.path.join("temp", samplesetname, "wes_")
  
  wesmutations = postProcess(wesrefwm, AllSamplesetName if AllSamplesetName else samplesetname,
                             save_output=folder, doCleanup=True, mutCol="CGA_WES_AC", **kwargs)

  # renaming
  print('renaming')
  #wesrenaming = track.removeOlderVersions(names=set(
  #    wesmutations['DepMap_ID']), refsamples=wesrefwm.get_samples(),
  #    arxspan_id="arxspan_id", version="version", priority=priority)
  
  wesrenaming = h.fileToDict(folder+"sample_renaming.json")
  
  wesmutations = wesmutations[wesmutations.DepMap_ID.isin(wesrenaming.keys())].replace({
      'DepMap_ID': wesrenaming})
  wesmutations.to_csv(folder + 'somatic_mutations_latest.csv', index=None)

  # doing wgs
  print('doing wgs')
  folder=os.path.join("temp", samplesetname, "wgs_")
  
  wgsmutations = postProcess(wgsrefwm, "allcurrent", #AllSamplesetName if AllSamplesetName else samplesetname, 
                         save_output=folder, doCleanup=True, mutCol="CGA_WES_AC", **kwargs)

  # renaming
  print('renaming')
  #wgsrenaming = track.removeOlderVersions(names=set(
  #    wesmutations['DepMap_ID']), refsamples=wgsrefwm.get_samples(),
  #    arxspan_id="arxspan_id", version="version", priority=priority)

  wgsrenaming = h.fileToDict(folder+"sample_renaming.json")

  wgsmutations = wgsmutations[wgsmutations.DepMap_ID.isin(wgsrenaming.keys())].replace({
      'DepMap_ID': wgsrenaming})
  wgsmutations.to_csv(folder + 'somatic_mutations_latest.csv', index=None)

  # merge
  print('merging')
  folder = os.path.join("temp", samplesetname, "merged_")
  toadd = set(wgsmutations.DepMap_ID) - set(wesmutations.DepMap_ID)
  priomutations = wesmutations.append(
      wgsmutations[wgsmutations.DepMap_ID.isin(toadd)]).reset_index(drop=True)
  #normals = set(ccle_refsamples[ccle_refsamples.primary_disease=="normal"].arxspan_id)
  #mutations = mutations[~mutations.DepMap_ID.isin(normals)]
  priomutations.to_csv(folder+'somatic_mutations.csv', index=False)

  #making binary mutation matrices
  print("creating mutation matrices")
  # binary mutations matrices
  mut.mafToMat(priomutations[(priomutations.isDeleterious)]).astype(
      int).T.to_csv(folder+'somatic_mutations_boolmatrix_deleterious.csv')
  mut.mafToMat(priomutations[~(priomutations.isDeleterious | priomutations.isCOSMIChotspot | 
                               priomutations.isTCGAhotspot | 
                               priomutations['Variant_Classification'] == 'Silent')]).astype(int).T.to_csv(
      folder+'somatic_mutations_boolmatrix_other.csv')
  mut.mafToMat(priomutations[(priomutations.isCOSMIChotspot | priomutations.isTCGAhotspot)]).astype(
    int).T.to_csv(folder+'somatic_mutations_boolmatrix_hotspot.csv')


  # genotyped mutations matrices
  mut.mafToMat(priomutations[(priomutations.isDeleterious)], mode="genotype",
              minfreqtocall=0.05).T.to_csv(folder+'somatic_mutations_matrix_deleterious.csv')
  mut.mafToMat(priomutations[~(priomutations.isDeleterious | priomutations.isCOSMIChotspot | 
                               priomutations.isTCGAhotspot |
                               priomutations['Variant_Classification'] == 'Silent')], 
                mode="genotype", minfreqtocall=0.05).T.to_csv(
                  folder+'somatic_mutations_matrix_other.csv')
  mut.mafToMat(priomutations[(priomutations.isCOSMIChotspot | priomutations.isTCGAhotspot)],
              mode="genotype", minfreqtocall=0.05).T.to_csv(
                folder+'somatic_mutations_matrix_hotspot.csv')

  # adding lgacy datasetss
  print('add legacy datasets')
  legacy_hybridcapture = tc.get(name='mutations-da6a', file='legacy_hybridcapture_somatic_mutations')
  legacy_raindance = tc.get(name='mutations-da6a', file='legacy_raindance_somatic_mutations')
  legacy_rna = tc.get(name='mutations-da6a', file='legacy_rna_somatic_mutations')
  legacy_wes_sanger = tc.get(name='mutations-da6a', file='legacy_wes_sanger_somatic_mutations')
  legacy_wgs_exoniconly = tc.get(name='mutations-da6a', file='legacy_wgs_exoniconly_somatic_mutations')

  merged = mut.mergeAnnotations(
      priomutations, legacy_hybridcapture, "HC_AC", useSecondForConflict=True, dry_run=False)
  merged = mut.mergeAnnotations(
    merged, legacy_raindance, "RD_AC", useSecondForConflict=True, dry_run=False)
  merged = mut.mergeAnnotations(
    merged, legacy_wgs_exoniconly, "WGS_AC", useSecondForConflict=False, dry_run=False)
  merged = mut.mergeAnnotations(
    merged, legacy_wes_sanger, "SangerWES_AC", useSecondForConflict=False, dry_run=False)
  merged = mut.mergeAnnotations(
    merged, legacy_rna, "RNAseq_AC", useSecondForConflict=False, dry_run=False)

  merged = merged[merged['tumor_f'] > 0.05]
  merged = annotateLikelyImmortalized(merged, TCGAlocs=[
                                                'TCGAhsCnt', 'COSMIChsCnt'], max_recurrence=0.05, 
                                                min_tcga_true_cancer=5)
  print("changing variant annotations")
  rename = {}
  for k,v in mutation_groups.items():
    for e in v:
      rename[e] = k
  merged['Variant_annotation'] = [rename[i] for i in merged['Variant_Classification'].tolist()]

  print('compare to previous release')
  a = set(merged.DepMap_ID)
  # tc.get(name='internal-20q2-7f46', version=18, file='CCLE_mutations')
  b = set(prev.DepMap_ID)
  print("new lines:")
  print(a-b)
  print('lost lines:')
  print(b-a)

  # making a depmap version
  #reverting to previous versions
  merged = merged[['Hugo_Symbol', 'Entrez_Gene_Id', 'NCBI_Build', 'Chromosome',
        'Start_position', 'End_position', 'Strand', 'Variant_Classification',
        'Variant_Type', 'Reference_Allele', 'Tumor_Allele', 'dbSNP_RS',
        'dbSNP_Val_Status', 'Genome_Change', 'Annotation_Transcript',
        'DepMap_ID', 'cDNA_Change', 'Codon_Change', 'Protein_Change', 'isDeleterious',
        'isTCGAhotspot', 'TCGAhsCnt', 'isCOSMIChotspot', 'COSMIChsCnt',
        'ExAC_AF',"Variant_annotation", 'CGA_WES_AC', 'HC_AC',
        'RD_AC', 'RNAseq_AC', 'SangerWES_AC', 'WGS_AC']].rename(columns={
          "Tumor_Allele":"Tumor_Seq_Allele1"})
  # removing immortalized ffor now 
  merged = merged[merged.is_likely_immortalization!=True]

  merged.to_csv(folder+'somatic_mutations_withlegacy.csv', index=False)

  # making binary matrices
  merged = merged[merged['Entrez_Gene_Id'] != 0]
  merged['mutname'] = merged['Hugo_Symbol'] + " (" + merged["Entrez_Gene_Id"].astype(str) + ")"
  mut.mafToMat(merged[(merged.Variant_annotation=="damaging")], mode='bool', 
    mutNameCol="mutname").astype(int).T.to_csv(folder+'somatic_mutations_boolmatrix_fordepmap_damaging.csv')
  mut.mafToMat(merged[(merged.Variant_annotation=="other conserving")], mode='bool', 
    mutNameCol="mutname").astype(int).T.to_csv(folder+'somatic_mutations_boolmatrix_fordepmap_othercons.csv')
  mut.mafToMat(merged[(merged.Variant_annotation=="other non-conserving")], mode='bool', 
    mutNameCol="mutname").astype(int).T.to_csv(folder+'somatic_mutations_boolmatrix_fordepmap_othernoncons.csv')
  mut.mafToMat(merged[(merged.isCOSMIChotspot | merged.isTCGAhotspot)], mode='bool', 
    mutNameCol="mutname").astype(int).T.to_csv(folder+'somatic_mutations_boolmatrix_fordepmap_hotspot.csv')

  # uploading to taiga
  tc.update_dataset(changes_description="new "+samplesetname+" release!",
                    dataset_permaname=taiga_dataset,
                    upload_files=[
                      # for depmap
                        {
                            "path": folder+"somatic_mutations_boolmatrix_fordepmap_hotspot.csv",
                            "format": "NumericMatrixCSV",
                            "encoding": "utf-8"
                        },
                        {
                            "path": folder+"somatic_mutations_boolmatrix_fordepmap_othernoncons.csv",
                            "format": "NumericMatrixCSV",
                            "encoding": "utf-8"
                        },
                        {
                            "path": folder+"somatic_mutations_boolmatrix_fordepmap_damaging.csv",
                            "format": "NumericMatrixCSV",
                            "encoding": "utf-8"
                        },
                      # genotyped
                        {
                            "path": folder+"somatic_mutations_matrix_hotspot.csv",
                            "format": "NumericMatrixCSV",
                            "encoding": "utf-8"
                        },
                        {
                            "path": folder+"somatic_mutations_matrix_other.csv",
                            "format": "NumericMatrixCSV",
                            "encoding": "utf-8"
                        },
                        {
                            "path": folder+"somatic_mutations_matrix_deleterious.csv",
                            "format": "NumericMatrixCSV",
                            "encoding": "utf-8"
                        },
                      # new
                        {
                            "path": folder+"somatic_mutations_boolmatrix_fordepmap_hotspot.csv",
                            "format": "NumericMatrixCSV",
                            "encoding": "utf-8"
                        },
                        {
                            "path": folder+"somatic_mutations_boolmatrix_fordepmap_othernoncons.csv",
                            "format": "NumericMatrixCSV",
                            "encoding": "utf-8"
                        },
                        {
                            "path": folder+"somatic_mutations_boolmatrix_fordepmap_damaging.csv",
                            "format": "NumericMatrixCSV",
                            "encoding": "utf-8"
                        },
                        {
                            "path": folder+"somatic_mutations_withlegacy.csv",
                            "format": "TableCSV",
                            "encoding": "utf-8"
                        },
                        {
                            "path": folder+"somatic_mutations.csv",
                            "format": "TableCSV",
                            "encoding": "utf-8"
                        },
                        {
                            "path": 'temp/'+samplesetname+"/wes_somatic_mutations_all.csv",
                            "format": "TableCSV",
                            "encoding": "utf-8"
                        },
                        {
                            "path": 'temp/'+samplesetname+"/wgs_somatic_mutations_all.csv",
                            "format": "TableCSV",
                            "encoding": "utf-8"
                        },
                    ],
                    add_all_existing_files=True,
                    upload_async=False,
                    dataset_description=Mutationsreadme)
