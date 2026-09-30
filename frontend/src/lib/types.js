/**
 * Core Data Models & Constants
 */

export const THEMES = [
  { id: 'catppuccin-mocha', name: 'Catppuccin Mocha', bg: '#1e1e2e', fg: '#cdd6f4', accent: '#89b4fa' },
  { id: 'catppuccin-latte', name: 'Catppuccin Latte', bg: '#eff1f5', fg: '#4c4f69', accent: '#1e66f5' },
  { id: 'nord', name: 'Nord Arctic', bg: '#2e3440', fg: '#eceff4', accent: '#88c0d0' },
  { id: 'solarized', name: 'Solarized Dark', bg: '#002b36', fg: '#fdf6e3', accent: '#268bd2' },
  { id: 'amoled', name: 'True AMOLED Black', bg: '#000000', fg: '#ffffff', accent: '#38bdf8' }
];

export const MATH_SYMBOLS = {
  Calculus: [
    { label: '∫ dx', latex: '\\int_{a}^{b} f(x) \\, dx' },
    { label: '∬ dA', latex: '\\iint_{D} f(x, y) \\, dA' },
    { label: 'd/dx', latex: '\\frac{d}{dx} \\left( f(x) \\right)' },
    { label: '∂/∂x', latex: '\\frac{\\partial f}{\\partial x}' },
    { label: 'lim', latex: '\\lim_{x \\to 0} \\frac{\\sin(x)}{x}' },
    { label: '∑', latex: '\\sum_{i=1}^{n} a_i' },
    { label: '∏', latex: '\\prod_{k=1}^{n} k' }
  ],
  Algebra: [
    { label: 'Fraction', latex: '\\frac{a}{b}' },
    { label: 'Square Root', latex: '\\sqrt{x}' },
    { label: 'Nth Root', latex: '\\sqrt[n]{x}' },
    { label: 'x^n', latex: 'x^{n}' },
    { label: 'x_i', latex: 'x_{i}' },
    { label: '±', latex: '\\pm' },
    { label: '≠', latex: '\\neq' },
    { label: '≈', latex: '\\approx' }
  ],
  Greek: [
    { label: 'α', latex: '\\alpha' },
    { label: 'β', latex: '\\beta' },
    { label: 'γ', latex: '\\gamma' },
    { label: 'δ', latex: '\\delta' },
    { label: 'θ', latex: '\\theta' },
    { label: 'λ', latex: '\\lambda' },
    { label: 'μ', latex: '\\mu' },
    { label: 'π', latex: '\\pi' },
    { label: 'σ', latex: '\\sigma' },
    { label: 'ω', latex: '\\omega' },
    { label: 'Δ', latex: '\\Delta' },
    { label: 'Ω', latex: '\\Omega' }
  ],
  LinearAlgebra: [
    { label: '2x2 Matrix', latex: '\\begin{pmatrix} a & b \\\\ c & d \\end{pmatrix}' },
    { label: 'Vector v', latex: '\\vec{v} = \\begin{bmatrix} v_1 \\\\ v_2 \\\\ v_3 \\end{bmatrix}' },
    { label: 'Dot Product', latex: '\\vec{u} \\cdot \\vec{v}' },
    { label: 'Cross Product', latex: '\\vec{u} \\times \\vec{v}' },
    { label: 'Norm ||v||', latex: '\\|\\vec{v}\\|' }
  ]
};

export const MERMAID_TEMPLATES = [
  {
    name: 'Lecture Flowchart',
    code: `graph TD
    A[Glucose] -->|Glycolysis| B[2 Pyruvate]
    B -->|Link Reaction| C[2 Acetyl-CoA]
    C -->|Krebs Cycle| D[NADH & FADH2]
    D -->|Oxidative Phosphorylation| E[32-34 ATP]`
  },
  {
    name: 'Sequence Diagram',
    code: `sequenceDiagram
    autonumber
    Client->>Desktop: Tailscale mTLS Handshake
    Desktop-->>Client: Accept with Ed25519 Fingerprint
    Client->>Desktop: Sync Step 1 (State Vector)
    Desktop-->>Client: Binary CRDT Update Delta
    Note over Client,Desktop: In-sync (<50ms latency)`
  },
  {
    name: 'Class Hierarchy',
    code: `classDiagram
    class Note {
      +int id
      +string title
      +string content
      +byte[] crdt_state
      +verifyFactClaims()
    }
    class CourseDocument {
      +int id
      +string filename
      +int total_pages
    }
    Note --> CourseDocument : local RAG verification`
  }
];
