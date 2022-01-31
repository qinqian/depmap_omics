# Given a set of samples, combine segment files into a single file
# more information available at https://open-cravat.readthedocs.io/en/latest/2.-Command-line-usage.html
workflow bcftools_fix_ploidy {
    call run_fix_ploidy
}

task run_fix_ploidy {
    File vcf
    String on = "INFO/DP>10 & AF>0.9"
    String replace = "m/m"
 
    Int memory = 2
    Int boot_disk_size = 10
    Int num_threads = 1
    Int num_preempt = 5
    String docker = "dceoy/bcftools"

    command {
      set -euo pipefail

      bcftools +setGT ${vcf} -t q -i'${on} -n c:'${replace}' > ${basename(vcf)}
      gzip ${basename(vcf)}
    }

    output {
        File vcf_fixedploid="${basename(vcf)}.gz"
    }

    runtime {
        docker: docker
        bootDiskSizeGb: "${boot_disk_size}"
        memory: "${memory}GB"
        disks: "local-disk ${disk_space} HDD"
        cpu: "${num_threads}"
        preemptible: "${num_preempt}"
    }

    meta {
        author: "Jeremie Kalfon"
    }
}