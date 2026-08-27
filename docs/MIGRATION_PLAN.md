# Migration plan from AmpliconFlow 1.x

A migrated notebook is accepted only when it:

1. follows the 2.0 notebook structure;
2. has exactly one Papermill `parameters` cell;
3. is output-free as a template;
4. contains no server-specific absolute paths;
5. validates inputs and parameters early;
6. keeps method-defining scientific code visible;
7. includes primary references;
8. documents acceptance criteria;
9. executes on a representative experiment;
10. is compared with the corresponding 1.x output.

Suggested order:
- [ ] 01 Prepare data
- [ ] 02 Quality control / DADA2
- [ ] 03 Rarefaction analysis
- [ ] 04 Metataxonomy
- [ ] 05 Diversity analysis
- [ ] 06 Abundance analysis
- [ ] 07 LEfSe
- [ ] 08 PICRUSt2
- [ ] 09 ANCOM-BC2
- [ ] 10 Report
