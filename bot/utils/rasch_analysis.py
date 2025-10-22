import numpy as np
import pandas as pd
from girth import rasch_mml
from typing import Dict, Any


class RaschAnalyzer:
    """Performs Rasch model analysis using MML estimation (similar to TAM's tam.cmle)"""
    
    def __init__(self):
        self.difficulty = None
        self.person_abilities = None
        self.model_fit = None
        
    def fit(self, data: pd.DataFrame) -> Dict[str, Any]:
        """
        Fit Rasch model to dichotomous response data
        
        Args:
            data: DataFrame with items as columns, persons as rows
                  Values should be 0 (incorrect) or 1 (correct)
        
        Returns:
            Dictionary containing analysis results
        """
        response_matrix = data.values
        
        self.difficulty = rasch_mml(response_matrix)
        
        self.person_abilities = self._estimate_person_abilities(
            response_matrix, self.difficulty
        )
        
        results = {
            'item_difficulty': self.difficulty,
            'person_ability': self.person_abilities,
            'n_items': response_matrix.shape[1],
            'n_persons': response_matrix.shape[0],
            'item_names': list(data.columns),
            'descriptive_stats': self._get_descriptive_stats(data),
            'reliability': self._estimate_reliability(response_matrix, self.difficulty)
        }
        
        return results
    
    def _estimate_person_abilities(self, responses: np.ndarray, 
                                   difficulty: np.ndarray) -> np.ndarray:
        """Estimate person abilities using MLE"""
        n_persons = responses.shape[0]
        abilities = np.zeros(n_persons)
        
        for i in range(n_persons):
            person_responses = responses[i, :]
            valid_idx = ~np.isnan(person_responses)
            
            if not np.any(valid_idx):
                abilities[i] = np.nan
                continue
                
            valid_responses = person_responses[valid_idx]
            valid_difficulty = difficulty[valid_idx]
            
            total_score = np.sum(valid_responses)
            if total_score == 0:
                abilities[i] = -3.0  
            elif total_score == len(valid_responses):
                abilities[i] = 3.0  
            else:
                abilities[i] = self._mle_ability(valid_responses, valid_difficulty)
        
        return abilities
    
    def _mle_ability(self, responses: np.ndarray, difficulty: np.ndarray, 
                     max_iter: int = 50, tol: float = 1e-6) -> float:
        """Maximum likelihood estimation of person ability"""
        theta = 0.0  
        
        for _ in range(max_iter):
            p = 1 / (1 + np.exp(-(theta - difficulty)))
            
            first_deriv = np.sum(responses - p)
            second_deriv = -np.sum(p * (1 - p))
            
            if abs(second_deriv) < 1e-10:
                break
                
            delta = first_deriv / second_deriv
            theta -= delta
            
            if abs(delta) < tol:
                break
        
        return theta
    
    def _get_descriptive_stats(self, data: pd.DataFrame) -> Dict[str, Any]:
        """Calculate descriptive statistics for items"""
        stats = {
            'item_means': data.mean().to_dict(),
            'item_sd': data.std().to_dict(),
            'total_scores': data.sum(axis=1).describe().to_dict()
        }
        return stats
    
    def _estimate_reliability(self, responses: np.ndarray, 
                             difficulty: np.ndarray) -> float:
        """Estimate person separation reliability (similar to Cronbach's alpha)"""
        person_scores = np.sum(responses, axis=1)
        observed_variance = np.var(person_scores)
        
        if observed_variance == 0:
            return 0.0
        
        expected_variance = np.mean(
            [self._expected_score_variance(difficulty) for _ in range(len(responses))]
        )
        
        reliability = (observed_variance - expected_variance) / observed_variance
        return max(0.0, min(1.0, reliability))
    
    def _expected_score_variance(self, difficulty: np.ndarray) -> float:
        """Calculate expected score variance"""
        theta = 0.0  
        p = 1 / (1 + np.exp(-(theta - difficulty)))
        return np.sum(p * (1 - p))
    
    def get_summary(self, results: Dict[str, Any]) -> str:
        """Generate a text summary of the analysis"""
        summary = []
        summary.append("=" * 60)
        summary.append("RASCH MODEL ANALYSIS RESULTS (MML Estimation)")
        summary.append("=" * 60)
        summary.append(f"\nSample Size: {results['n_persons']} persons")
        summary.append(f"Number of Items: {results['n_items']} items")
        summary.append(f"\nReliability: {results['reliability']:.3f}")
        
        summary.append("\n" + "-" * 60)
        summary.append("ITEM DIFFICULTY PARAMETERS")
        summary.append("-" * 60)
        summary.append(f"{'Item':<20} {'Difficulty':>12} {'Mean':>12}")
        summary.append("-" * 60)
        
        for i, item_name in enumerate(results['item_names']):
            difficulty = results['item_difficulty'][i]
            mean = results['descriptive_stats']['item_means'][item_name]
            summary.append(f"{item_name:<20} {difficulty:>12.3f} {mean:>12.3f}")
        
        summary.append("\n" + "-" * 60)
        summary.append("PERSON ABILITY DISTRIBUTION")
        summary.append("-" * 60)
        abilities = results['person_ability']
        valid_abilities = abilities[~np.isnan(abilities)]
        
        if len(valid_abilities) > 0:
            summary.append(f"Mean:   {np.mean(valid_abilities):>8.3f}")
            summary.append(f"SD:     {np.std(valid_abilities):>8.3f}")
            summary.append(f"Min:    {np.min(valid_abilities):>8.3f}")
            summary.append(f"Max:    {np.max(valid_abilities):>8.3f}")
        
        summary.append("\n" + "=" * 60)
        
        return "\n".join(summary)
