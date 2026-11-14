-- Optional ordinary catalog metadata labels. Requires UC table permissions.
-- Do not use tag values to store secrets, user identifiers or medical data.
ALTER TABLE rag_portfolio.bronze_documents
  SET TAGS ('data_classification' = 'synthetic', 'data_layer' = 'bronze');
ALTER TABLE rag_portfolio.silver_chunks
  SET TAGS ('data_classification' = 'synthetic', 'data_layer' = 'silver');
ALTER TABLE rag_portfolio.gold_retrieval_evaluation
  SET TAGS ('data_classification' = 'synthetic', 'data_layer' = 'gold');
