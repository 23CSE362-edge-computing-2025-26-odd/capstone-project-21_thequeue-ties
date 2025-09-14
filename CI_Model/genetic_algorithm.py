import random
import numpy as np

class GeneticAlgorithm:
    def __init__(self, jobs_data, population_size=40, generations=50, crossover_rate=0.85, mutation_rate=0.1, elitism_size=2):
        self.jobs_data = jobs_data
        self.population_size = population_size
        self.generations = generations
        self.crossover_rate = crossover_rate
        self.mutation_rate = mutation_rate
        self.elitism_size = elitism_size

    def _initialize_population(self):
        job_ids = list(self.jobs_data.keys())
        return [random.sample(job_ids, len(job_ids)) for _ in range(self.population_size)]

    def _calculate_fitness(self, schedule):
        makespan = 0
        total_energy = 0
        weighted_tardiness = 0
        machine_finish_times = {}

        for job_id in schedule:
            job_info = self.jobs_data[job_id]
            job_priority = job_info['priority']
            current_op_finish_time = 0
            for op in job_info['operations']:
                start_time = max(machine_finish_times.get(op['machine'], 0), current_op_finish_time)
                job_completion_time = start_time + op['time']
                machine_finish_times[op['machine']] = job_completion_time
                current_op_finish_time = job_completion_time
                total_energy += op['time'] * op['power']
            makespan = max(makespan, job_completion_time)
            weighted_tardiness += job_completion_time * job_priority

        score = (0.5 * makespan) + (0.3 * weighted_tardiness) + (0.2 * total_energy)
        return 1 / (score + 1)

    def _order_crossover(self, parent1, parent2):
        n = len(parent1)
        a, b = sorted(random.sample(range(n), 2))
        child = [None] * n
        child[a:b+1] = parent1[a:b+1]
        
        p = 0
        for gene in parent2:
            if gene not in child:
                while child[p] is not None:
                    p += 1
                child[p] = gene
        return child

    def _mutate(self, schedule):
        if random.random() < self.mutation_rate:
            idx1, idx2 = random.sample(range(len(schedule)), 2)
            schedule[idx1], schedule[idx2] = schedule[idx2], schedule[idx1]
        return schedule

    def run(self):
        population = self._initialize_population()
        
        for _ in range(self.generations):
            fitness_scores = [self._calculate_fitness(ind) for ind in population]
            
            # Elitism: carry over the best individuals
            elite_indices = np.argsort(fitness_scores)[-self.elitism_size:]
            next_generation = [population[i] for i in elite_indices]

            # Tournament Selection
            while len(next_generation) < self.population_size:
                p1 = random.choices(population, weights=fitness_scores, k=1)[0]
                p2 = random.choices(population, weights=fitness_scores, k=1)[0]
                
                if random.random() < self.crossover_rate:
                    child = self._order_crossover(p1, p2)
                else:
                    child = p1[:] # Crossover failed, just clone a parent
                
                next_generation.append(self._mutate(child))
            
            population = next_generation

        final_fitness_scores = [self._calculate_fitness(ind) for ind in population]
        best_schedule = population[np.argmax(final_fitness_scores)]
        return best_schedule