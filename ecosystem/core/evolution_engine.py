# ecosystem/core/evolution_engine.py
"""
Genetic evolution engine: Chromosome, Population, GeneticOperators, EvolutionEngine.

Implements a classic genetic algorithm with:
- Real-valued chromosome representation
- Gaussian mutation and single-point crossover
- Tournament selection
- Fitness-proportional evolution tracking

Also provides EvolutionEngineAdapter for Hermes integration.
"""

from __future__ import annotations

import logging
import random
from dataclasses import dataclass, field
from typing import Any, Callable

logger = logging.getLogger("polis.evolution_adapter")


@dataclass
class Chromosome:
    genes: list[float]
    fitness: float = 0.0

    def __post_init__(self):
        self.genes = list(self.genes)

    def copy(self) -> Chromosome:
        return Chromosome(genes=list(self.genes), fitness=self.fitness)


@dataclass
class Population:
    size: int
    gene_length: int
    individuals: list[Chromosome] = field(default_factory=list)

    def __post_init__(self):
        if not self.individuals:
            self.individuals = [
                Chromosome(genes=[random.random() for _ in range(self.gene_length)])
                for _ in range(self.size)
            ]

    def evaluate_fitness(self, fitness_fn: Callable[[list[float]], float]) -> None:
        for ind in self.individuals:
            ind.fitness = fitness_fn(ind.genes)

    def get_fittest(self) -> Chromosome | None:
        if not self.individuals:
            return None
        return max(self.individuals, key=lambda x: x.fitness)


class GeneticOperators:
    @staticmethod
    def mutate(chrom: Chromosome, rate: float = 0.1, sigma: float = 0.1) -> None:
        for i in range(len(chrom.genes)):
            if random.random() < rate:
                chrom.genes[i] = max(0.0, min(1.0, chrom.genes[i] + random.gauss(0, sigma)))

    @staticmethod
    def crossover(
        parent1: Chromosome,
        parent2: Chromosome,
        rate: float = 0.8,
    ) -> tuple[Chromosome, Chromosome]:
        child1 = parent1.copy()
        child2 = parent2.copy()
        if random.random() < rate and len(parent1.genes) > 1:
            point = random.randint(1, len(parent1.genes) - 1)
            child1.genes = parent1.genes[:point] + parent2.genes[point:]
            child2.genes = parent2.genes[:point] + parent1.genes[point:]
        return child1, child2

    @staticmethod
    def tournament_selection(
        population: Population,
        tournament_size: int = 3,
    ) -> tuple[Chromosome, Chromosome]:
        def _select() -> Chromosome:
            contestants = random.sample(
                population.individuals,
                min(tournament_size, len(population.individuals)),
            )
            return max(contestants, key=lambda x: x.fitness)

        return _select(), _select()


class EvolutionEngine:
    def __init__(
        self,
        population_size: int = 50,
        gene_length: int = 10,
        mutation_rate: float = 0.1,
        crossover_rate: float = 0.8,
        elitism: int = 2,
    ):
        self.population = Population(size=population_size, gene_length=gene_length)
        self.generation = 0
        self.mutation_rate = mutation_rate
        self.crossover_rate = crossover_rate
        self.elitism = elitism
        self.history: list[dict[str, float]] = []
        self.best_fitness_history: list[float] = []

    def evolve(
        self,
        fitness_fn: Callable[[list[float]], float],
        generations: int = 1,
    ) -> None:
        for _ in range(generations):
            self.population.evaluate_fitness(fitness_fn)
            current_best = self.population.get_fittest()
            self.best_fitness_history.append(current_best.fitness if current_best else 0.0)

            sorted_individuals = sorted(
                self.population.individuals,
                key=lambda x: x.fitness,
                reverse=True,
            )
            elites = [ind.copy() for ind in sorted_individuals[: self.elitism]]

            new_individuals: list[Chromosome] = []
            while len(new_individuals) < self.population.size - self.elitism:
                p1, p2 = GeneticOperators.tournament_selection(self.population)
                c1, c2 = GeneticOperators.crossover(p1, p2, self.crossover_rate)
                GeneticOperators.mutate(c1, self.mutation_rate)
                GeneticOperators.mutate(c2, self.mutation_rate)
                new_individuals.extend([c1, c2])

            self.population.individuals = elites + new_individuals[: self.population.size - self.elitism]
            self.generation += 1

        self.population.evaluate_fitness(fitness_fn)
        final_best = self.population.get_fittest()
        self.best_fitness_history.append(final_best.fitness if final_best else 0.0)
        self.history.append({
            "generation": self.generation,
            "best_fitness": final_best.fitness if final_best else 0.0,
            "avg_fitness": (
                sum(i.fitness for i in self.population.individuals) / len(self.population.individuals)
                if self.population.individuals
                else 0.0
            ),
        })

    def get_best(self) -> Chromosome | None:
        return self.population.get_fittest()


class EvolutionEngineAdapter:
    """
    进化引擎适配器

    将 Hermes 的进化调用映射到 ecosystem/evolution.py
    """

    def __init__(self, data_dir: str = None):
        import os
        self.data_dir = data_dir or os.environ.get(
            "CITY_STATE_DATA_DIR",
            r"C:\Users\dfhai\AppData\Roaming\TRAE SOLO CN\ModularData\ai-agent\work-mode-projects\6a45044b9f3d6718577ed1f8\city_state_data\ecosystem"
        )
        self._engine = None

    def _get_engine(self):
        if self._engine is None:
            from ecosystem.evolution import EvolutionEngine
            self._engine = EvolutionEngine(data_dir=self.data_dir)
        return self._engine

    def run_evolution(self, agent_ids: list[str] = None,
                      generations: int = 1,
                      stress_factor: float = 1.0) -> dict:
        engine = self._get_engine()
        if not agent_ids:
            genomes = engine.db.list_genomes(limit=100)
            agent_ids = [g.agent_id for g in genomes]
        if len(agent_ids) < 4:
            logger.warning(f"种群太小: {len(agent_ids)}，无法进化")
            return {"error": "种群太小", "population": len(agent_ids)}
        stats = engine.db.get_statistics()
        current_gen = stats.get('latest_generation', 0)
        results = []
        for i in range(generations):
            result = engine.evolve_generation(
                agent_ids,
                generation=current_gen + i + 1,
                top_ratio=0.4,
                stress_factor=stress_factor
            )
            results.append(result)
            genomes = engine.db.list_genomes(limit=100)
            agent_ids = [g.agent_id for g in genomes]
        return {
            "generations": generations,
            "final_generation": current_gen + generations,
            "final_avg_iq": results[-1].get("avg_iq") if results else 0,
            "final_diversity": results[-1].get("diversity", 0) if results else 0,
            "results": results
        }

    def get_chromosomes(self, limit: int = 10) -> list[dict]:
        engine = self._get_engine()
        genomes = engine.db.list_genomes(limit=limit)
        return [g.to_dict() for g in genomes]

    def create_genome(self, agent_id: str, generation: int = 0) -> dict:
        engine = self._get_engine()
        genome = engine.create_agent_genome(agent_id, generation)
        return genome.to_dict()

    def close(self):
        if self._engine:
            self._engine.close()
            self._engine = None
