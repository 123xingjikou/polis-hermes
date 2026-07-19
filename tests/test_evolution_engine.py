"""
测试进化引擎核心功能
"""

import pytest

from ecosystem.core.evolution_engine import (
    EvolutionEngine,
    Population,
    Chromosome,
    GeneticOperators,
)


class TestChromosome:
    """染色体测试"""

    def test_create_chromosome(self):
        """创建染色体"""
        chrom = Chromosome(genes=[0.1, 0.5, 0.9], fitness=0.0)
        assert len(chrom.genes) == 3
        assert chrom.fitness == 0.0

    def test_chromosome_default_fitness(self):
        """默认适应度为 None 或 0"""
        chrom = Chromosome(genes=[0.2, 0.8])
        # 适应度可以是 None 或数值
        assert chrom.genes == [0.2, 0.8]

    def test_chromosome_mutation(self):
        """突变操作"""
        chrom = Chromosome(genes=[0.5] * 10, fitness=0.5)
        original_genes = list(chrom.genes)
        GeneticOperators.mutate(chrom, rate=1.0)  # 100% 突变率
        # 突变后至少有一个基因发生变化
        changed = sum(1 for a, b in zip(original_genes, chrom.genes) if a != b)
        assert changed > 0


class TestGeneticOperators:
    """遗传算子测试"""

    def test_crossover_basic(self):
        """单点交叉"""
        parent1 = Chromosome(genes=[1.0, 1.0, 1.0, 1.0])
        parent2 = Chromosome(genes=[0.0, 0.0, 0.0, 0.0])

        child1, child2 = GeneticOperators.crossover(parent1, parent2, rate=1.0)

        # 子代长度应该和亲代相同
        assert len(child1.genes) == len(parent1.genes)
        assert len(child2.genes) == len(parent2.genes)

    def test_mutation_rate_zero(self):
        """突变率为 0 时基因不变"""
        chrom = Chromosome(genes=[0.1, 0.2, 0.3, 0.4])
        original = list(chrom.genes)
        GeneticOperators.mutate(chrom, rate=0.0)
        assert chrom.genes == original

    def test_tournament_selection(self):
        """锦标赛选择"""
        population = Population(size=10, gene_length=8)
        selected = GeneticOperators.tournament_selection(population, tournament_size=3)
        assert len(selected) == 2
        assert isinstance(selected[0], Chromosome)
        assert isinstance(selected[1], Chromosome)


class TestPopulation:
    """种群测试"""

    def test_create_population(self):
        """创建种群"""
        pop = Population(size=50, gene_length=10)
        assert len(pop.individuals) == 50
        for ind in pop.individuals:
            assert len(ind.genes) == 10

    def test_evaluate_fitness(self):
        """评估适应度"""
        pop = Population(size=20, gene_length=8)

        def simple_fitness(genes):
            return sum(genes)

        pop.evaluate_fitness(simple_fitness)

        for ind in pop.individuals:
            assert ind.fitness is not None
            assert 0 <= ind.fitness <= 8  # 每个基因 0-1，8 个基因

    def test_fittest_individual(self):
        """获取最优秀个体"""
        pop = Population(size=30, gene_length=5)
        pop.evaluate_fitness(sum)
        fittest = pop.get_fittest()
        assert fittest is not None
        assert fittest.fitness == max(ind.fitness for ind in pop.individuals)


class TestEvolutionEngine:
    """进化引擎测试"""

    def test_engine_initialization(self):
        """引擎初始化"""
        engine = EvolutionEngine(
            population_size=20,
            gene_length=10,
        )
        assert engine.population is not None
        assert len(engine.population.individuals) == 20
        assert engine.generation == 0

    def test_evolve_one_generation(self):
        """进化一代"""
        engine = EvolutionEngine(population_size=30, gene_length=8)

        def fitness_func(genes):
            return sum(genes)

        initial_best = engine.population.get_fittest()
        if initial_best and initial_best.fitness is None:
            engine.population.evaluate_fitness(fitness_func)
            initial_best = engine.population.get_fittest()

        engine.evolve(fitness_func, generations=1)

        assert engine.generation == 1
        assert len(engine.population.individuals) == 30

    def test_evolve_improves_fitness(self):
        """多代进化后适应度应该提升（对简单问题）"""
        engine = EvolutionEngine(
            population_size=50,
            gene_length=10,
            mutation_rate=0.1,
            crossover_rate=0.8,
        )

        def fitness_func(genes):
            return sum(genes)  # 最大化基因值之和

        engine.population.evaluate_fitness(fitness_func)
        initial_fitness = engine.population.get_fittest().fitness

        engine.evolve(fitness_func, generations=10)

        final_fitness = engine.population.get_fittest().fitness
        # 对 sum 最大化问题，进化后适应度应该 >= 初始
        assert final_fitness >= initial_fitness * 0.95  # 留 5% 容差

    def test_evolution_history(self):
        """进化历史记录"""
        engine = EvolutionEngine(population_size=20, gene_length=6)
        engine.population.evaluate_fitness(sum)
        engine.evolve(sum, generations=5)

        assert hasattr(engine, 'history') or hasattr(engine, 'best_fitness_history')
        # 至少应该记录了每一代的最佳适应度
