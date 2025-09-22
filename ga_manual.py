import random
import numpy as np

class GeneticAlgorithm:
    def __init__(self, fitness_func, param_bounds_low, param_bounds_high, pop_size, chromosome_len, crossover_rate, mutation_rate):
        self.fitness_func = fitness_func
        self.param_bounds_low = param_bounds_low
        self.param_bounds_high = param_bounds_high
        self.pop_size = pop_size
        self.chromosome_len = chromosome_len
        self.crossover_rate = crossover_rate
        self.mutation_rate = mutation_rate
        self.population = self._initialize_population()

    def _ensure_constraints(self, individual):
        # Temperature parameters [t_norm_mid, t_hot_start, t_hot_mid]
        if individual[0] > individual[1]: individual[0], individual[1] = individual[1], individual[0]
        if individual[1] > individual[2]: individual[1], individual[2] = individual[2], individual[1]
        # Vibration parameters [v_low_mid, v_med_start, v_med_mid, v_med_end, v_high_start, v_high_mid]
        vib_params = sorted(individual[3:9])
        individual[3:9] = vib_params
        return individual

    def _initialize_population(self):
        population = []
        for _ in range(self.pop_size):
            individual = [random.uniform(self.param_bounds_low[i], self.param_bounds_high[i]) for i in range(self.chromosome_len)]
            population.append(self._ensure_constraints(individual))
        return population

    def _selection(self, fitness_scores):
        tournament_size = 5
        contender_indices = random.sample(range(self.pop_size), tournament_size)
        valid_contenders = {i: fitness_scores[i] for i in contender_indices if fitness_scores[i] is not None}
        if not valid_contenders: return random.choice(self.population)
        best_contender_index = max(valid_contenders, key=valid_contenders.get)
        return self.population[best_contender_index]

    def _crossover(self, parent1, parent2):
        if random.random() < self.crossover_rate:
            point = random.randint(1, self.chromosome_len - 1)
            child1 = self._ensure_constraints(parent1[:point] + parent2[point:])
            child2 = self._ensure_constraints(parent2[:point] + parent1[point:])
            return child1, child2
        return parent1, parent2

    def _mutate(self, individual):
        for i in range(self.chromosome_len):
            if random.random() < self.mutation_rate:
                change = random.uniform(-5.0, 5.0)
                individual[i] = max(self.param_bounds_low[i], min(individual[i] + change, self.param_bounds_high[i]))
        return self._ensure_constraints(individual)

    def run(self, generations):
        best_overall_individual, best_overall_fitness = None, -float('inf')
        for gen in range(generations):
            fitness_scores = [self.fitness_func(ind) for ind in self.population]
            valid_scores = [s for s in fitness_scores if s is not None and s != -float('inf')]
            if not valid_scores:
                print(f"Generation {gen + 1}/{generations} | All individuals failed. Re-initializing.")
                self.population = self._initialize_population()
                continue
            
            best_fitness_in_gen = max(valid_scores)
            best_individual_in_gen = self.population[fitness_scores.index(best_fitness_in_gen)]

            if best_fitness_in_gen > best_overall_fitness:
                best_overall_fitness, best_overall_individual = best_fitness_in_gen, best_individual_in_gen
            
            print(f"Generation {gen + 1}/{generations} | Best Fitness: {best_fitness_in_gen:.2f} | Overall Best: {best_overall_fitness:.2f}")

            next_population = [best_overall_individual]
            while len(next_population) < self.pop_size:
                p1, p2 = self._selection(fitness_scores), self._selection(fitness_scores)
                c1, c2 = self._crossover(p1, p2)
                next_population.append(self._mutate(c1))
                if len(next_population) < self.pop_size:
                    next_population.append(self._mutate(c2))
            self.population = next_population
        return best_overall_individual, best_overall_fitness