
"""
Math plugin for advanced mathematical calculations.
"""

import math
import re
import logging
from typing import Dict, Any, Optional


class MathPlugin:
    """Advanced mathematical calculations plugin."""
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self.supported_functions = {
            'sin', 'cos', 'tan', 'asin', 'acos', 'atan',
            'sinh', 'cosh', 'tanh', 'log', 'log10', 'exp',
            'sqrt', 'factorial', 'ceil', 'floor', 'abs'
        }
    
    def can_handle(self, text: str) -> bool:
        """Check if this plugin can handle the given text."""
        math_indicators = [
            'calculate', 'compute', 'solve', 'math', 'equation',
            'sin', 'cos', 'tan', 'log', 'sqrt', 'factorial',
            'derivative', 'integral', 'matrix'
        ]
        
        text_lower = text.lower()
        return any(indicator in text_lower for indicator in math_indicators)
    
    def process(self, text: str, context: Dict[str, Any] = None) -> Dict[str, Any]:
        """Process mathematical request."""
        try:
            # Extract mathematical expression
            expression = self._extract_expression(text)
            
            if not expression:
                return {
                    "success": False,
                    "response": "I couldn't find a mathematical expression to calculate."
                }
            
            # Calculate result
            result = self._calculate(expression)
            
            if result is not None:
                return {
                    "success": True,
                    "response": f"The result is {result}",
                    "expression": expression,
                    "result": result
                }
            else:
                return {
                    "success": False,
                    "response": "I couldn't calculate that expression."
                }
                
        except Exception as e:
            self.logger.error(f"Math plugin error: {e}")
            return {
                "success": False,
                "response": f"Calculation error: {str(e)}"
            }
    
    def _extract_expression(self, text: str) -> Optional[str]:
        """Extract mathematical expression from text."""
        # Look for various mathematical patterns
        patterns = [
            r'(\d+\.?\d*\s*[\+\-\*\/\%\^]\s*\d+\.?\d*)',
            r'(sin\(\d+\.?\d*\))',
            r'(cos\(\d+\.?\d*\))',
            r'(tan\(\d+\.?\d*\))',
            r'(sqrt\(\d+\.?\d*\))',
            r'(log\(\d+\.?\d*\))',
            r'(\d+\.?\d*\s*factorial)',
            r'(\d+\.?\d*\s*squared)',
            r'(\d+\.?\d*\s*cubed)'
        ]
        
        for pattern in patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                return match.group(1)
        
        return None
    
    def _calculate(self, expression: str) -> Optional[float]:
        """Safely calculate mathematical expression."""
        try:
            # Handle special cases
            if 'factorial' in expression.lower():
                number = re.search(r'(\d+)', expression)
                if number:
                    return math.factorial(int(number.group(1)))
            
            if 'squared' in expression.lower():
                number = re.search(r'(\d+\.?\d*)', expression)
                if number:
                    return float(number.group(1)) ** 2
            
            if 'cubed' in expression.lower():
                number = re.search(r'(\d+\.?\d*)', expression)
                if number:
                    return float(number.group(1)) ** 3
            
            # Handle trigonometric functions
            for func in ['sin', 'cos', 'tan']:
                if func in expression.lower():
                    match = re.search(f'{func}\\((\\d+\\.?\\d*)\\)', expression, re.IGNORECASE)
                    if match:
                        angle = math.radians(float(match.group(1)))
                        return getattr(math, func)(angle)
            
            # Handle other functions
            if 'sqrt(' in expression.lower():
                match = re.search(r'sqrt\((\d+\.?\d*)\)', expression, re.IGNORECASE)
                if match:
                    return math.sqrt(float(match.group(1)))
            
            if 'log(' in expression.lower():
                match = re.search(r'log\((\d+\.?\d*)\)', expression, re.IGNORECASE)
                if match:
                    return math.log(float(match.group(1)))
            
            # Handle basic arithmetic
            expression = expression.replace('^', '**')
            
            # Validate expression
            if re.match(r'^[\d\+\-\*\/\%\.\(\)\s\*]+$', expression):
                return eval(expression)
            
        except Exception as e:
            self.logger.error(f"Calculation error: {e}")
        
        return None
