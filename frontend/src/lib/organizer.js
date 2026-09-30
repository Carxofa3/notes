/**
 * Smart Note & Folder Auto-Organizer
 * Automatically categorizes notes into existing user folders or proposes new folders
 * with semantic icon and color assignments.
 */

// Domain keyword mapping for intelligent icon and color classification
const TOPIC_RULES = [
  {
    regex: /bio|cell|dna|gene|rna|atp|organism|protein|enzyme|mitochondria|photosynthesis|ecology/i,
    icon: '🧬',
    color: '#10b981', // emerald
    suggestedFolder: 'Biology & Life Sciences'
  },
  {
    regex: /physic|quantum|force|velocity|gravity|thermodynamic|entropy|electromagnet|wave|newton|relativity/i,
    icon: '⚛️',
    color: '#3b82f6', // blue
    suggestedFolder: 'Physics & Dynamics'
  },
  {
    regex: /math|calculus|integral|derivativ|matrix|vector|linear algebra|algebra|topology|theorem|differential/i,
    icon: '📐',
    color: '#8b5cf6', // purple
    suggestedFolder: 'Calculus & Applied Math'
  },
  {
    regex: /chem|reaction|acid|base|organic|molecule|compound|periodic|molar|bonding|redox/i,
    icon: '🧪',
    color: '#06b6d4', // cyan
    suggestedFolder: 'Chemistry & Synthesis'
  },
  {
    regex: /code|python|rust|c\+\+|java|algorithm|data structure|api|sql|network|frontend|backend|os|linux|compiler/i,
    icon: '💻',
    color: '#f59e0b', // amber
    suggestedFolder: 'Computer Science & Software'
  },
  {
    regex: /neuro|brain|cognit|psycholog|neuron|synapse|memory|behavior/i,
    icon: '🧠',
    color: '#ec4899', // pink
    suggestedFolder: 'Neuroscience & Psychology'
  },
  {
    regex: /history|empire|war|revolution|treaty|century|dynasty|civilization|politic/i,
    icon: '🏛️',
    color: '#f43f5e', // rose
    suggestedFolder: 'History & Humanities'
  },
  {
    regex: /economy|market|finance|capital|gdp|inflation|elasticity|trade|investment/i,
    icon: '📊',
    color: '#14b8a6', // teal
    suggestedFolder: 'Economics & Markets'
  },
  {
    regex: /electric|circuit|volt|ohm|transistor|current|signal|impedance|fourier/i,
    icon: '⚡',
    color: '#eab308', // yellow
    suggestedFolder: 'Electronics & Circuits'
  }
];

export const PRESET_ICONS = [
  '📁', '📂', '📚', '🧬', '⚛️', '📐', '💻', '🔬',
  '🧠', '⚡', '📝', '🎯', '📊', '🏛️', '🧪', '🌐',
  '🎨', '📖', '🏷️', '💡', '📌', '🚀', '🔑', '🛠️'
];

export const PRESET_COLORS = [
  { name: 'Blue', hex: '#3b82f6' },
  { name: 'Emerald', hex: '#10b981' },
  { name: 'Purple', hex: '#8b5cf6' },
  { name: 'Amber', hex: '#f59e0b' },
  { name: 'Rose', hex: '#f43f5e' },
  { name: 'Cyan', hex: '#06b6d4' },
  { name: 'Pink', hex: '#ec4899' },
  { name: 'Slate', hex: '#64748b' }
];

/**
 * Automatically inspects note content & title against existing folders.
 * Returns either an existing folder match or a new folder suggestion with icon & color.
 */
export function analyzeAndCategorize(noteTitle = '', noteContent = '', existingUnits = []) {
  const fullText = `${noteTitle} ${noteContent}`.toLowerCase();
  
  // 1. Check if it matches any existing user folder
  let bestExistingUnit = null;
  let highestScore = 0;

  for (const unit of existingUnits) {
    const unitWords = (unit.name || '')
      .toLowerCase()
      .split(/[\s\-_/]+/)
      .filter(w => w.length > 2);
      
    let matchCount = 0;
    for (const word of unitWords) {
      if (fullText.includes(word)) {
        matchCount += 1;
      }
    }
    
    if (matchCount > highestScore && matchCount > 0) {
      highestScore = matchCount;
      bestExistingUnit = unit;
    }
  }

  // 2. Determine semantic icon & color
  let matchedRule = null;
  for (const rule of TOPIC_RULES) {
    if (rule.regex.test(fullText)) {
      matchedRule = rule;
      break;
    }
  }

  const icon = matchedRule?.icon || '📝';
  const color = matchedRule?.color || '#3b82f6';

  // 3. Formulate recommendation
  if (bestExistingUnit && highestScore >= 1) {
    return {
      type: 'existing_folder',
      unitId: bestExistingUnit.id,
      unitName: bestExistingUnit.name,
      suggestedIcon: bestExistingUnit.icon || icon,
      suggestedColor: bestExistingUnit.color || color,
      reason: `Matched existing folder "${bestExistingUnit.name}"`
    };
  }

  // 4. Propose a new folder
  let newFolderName = matchedRule ? matchedRule.suggestedFolder : 'General Notes';
  if (noteTitle && noteTitle.trim().length > 3 && !noteTitle.startsWith('Untitled') && !noteTitle.startsWith('New Lecture')) {
    newFolderName = `${noteTitle.trim()} Studies`;
  }

  return {
    type: 'new_folder',
    unitName: newFolderName,
    suggestedIcon: icon,
    suggestedColor: color,
    reason: matchedRule ? `Identified academic domain (${matchedRule.suggestedFolder})` : 'New topic detected'
  };
}
