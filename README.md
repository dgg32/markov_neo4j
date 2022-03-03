

# Introduction

  

  

This repository contains code and data for my article "(Hidden Markov Model with Neo4j)[https://dgg32.medium.com/hidden-markov-model-with-neo4j-660ecd15ed19]".

1. Both scripts are for data generation in Neo4j.


  

  

# Prerequisite

Neo4j Desktop
  

# Run


  
1. Generate the nodes. There are three examples, the second one is the one demonstrated in the article.
```console
python create_node.py [neo4j_ip_or_"localhost"] [neo4j_project_password] [1, 2 or 3]
```
 
2. Run the Viterbi algorithm
```console
python viterbi.py [neo4j_ip_or_"localhost"] [neo4j_project_password]   
```
3. Visualize the HMM states in Neo4j browser or Bloom.
  

## Authors

  

*  **Sixing Huang** - *Concept and Coding*

  

## License

  

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details
