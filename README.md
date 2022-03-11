

# Introduction

  

  

This repository contains code and data for my article "[Hidden Markov Model with Neo4j](https://medium.com/p/dde776f9047b)" and "[Train a Hidden Markov Model with Neo4j](https://dgg32.medium.com/train-a-hidden-markov-model-with-neo4j-a5547c9eb0d4)".

1. All scripts are for data generation in Neo4j.


  

  

# Prerequisite

Neo4j Desktop
  

# Run


  
1. Generate the nodes. There are three examples, the second one is the one demonstrated in the article.
```console
python create_node.py [neo4j_ip_or_"localhost"] [neo4j_project_password] [1, 2 or 3]
```
 
2. Run the Baum-Welch algorithm
```console
python baum.py [neo4j_ip_or_"localhost"] [neo4j_project_password] [how_many_iterations]

3. Run the Viterbi algorithm
```console
python viterbi.py [neo4j_ip_or_"localhost"] [neo4j_project_password]   
```
4. Visualize the HMM states in Neo4j browser or Bloom.
  

## Authors

  

*  **Sixing Huang** - *Concept and Coding*

  

## License

  

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details
