## Processes

The Processes of the *E. coli* model span several major areas of cellular physiology. We have clustered the Processes into the following groups, which we present in the order listed: Central Dogma, Metabolism, and Balanced Growth. We modeled Processes using the most appropriate mathematics for their individual network topology and degree of experimental characterization. Each process is a computational representation of chemical reactions or transformations grouped by a physiological function. The actual division of reactions across processes is a modeling decision made during model construction, and the number of Processes does not reflect their complexity or scope. The inputs and outputs of each Process are the counts of metabolites or macromolecules and the catalytic capacity or configuration of the enzymes that catalyze the reactions in each Process. This section details the model implementation, computational algorithm, associated data, and relevant code for each Process.

### Process Index

* [Cell Division](processes/cell_division.pdf)
* [Chromosome Replication](processes/chromosome_replication.pdf)
* [Complexation](processes/complexation.pdf)
* [Metabolism](processes/metabolism.pdf)
* [Protein Degradation](processes/protein_degradation.pdf)
* [RNA Degradation](processes/rna_degradation.pdf)
* [Transcription](processes/transcription.pdf)
* [Transcripton Regulation](processes/transcription_regulation.pdf)
* [Translation](processes/translation.pdf)

### Regeneration of pdf files from tex files

Assuming all the dependencies have been installed (try `sudo apt install texlive-full` on linux if not), the pdf files can be compiled from the tex files with:

      runscripts/fileManipulation/compile_process_pdf.sh docs/processes/src/<process>.tex
