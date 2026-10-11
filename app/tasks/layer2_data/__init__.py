# Importing the task here pulls it in while layer2_common is still loading:
# repository imports this package for the aggregation constants, and the task
# subclasses Layer2CatalogImportTask, which is not defined yet at that point.
