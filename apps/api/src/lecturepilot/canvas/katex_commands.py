"""KaTeX control words that render identically in the web canvas and generated PDFs."""

PORTABLE_KATEX_COMMANDS = frozenset(
    """
    Alpha Beta Chi Delta Epsilon Eta Gamma Iota Kappa Lambda Mu Nu Omega Omicron Phi Pi Psi
    Rho Sigma Tau Theta Upsilon Xi Zeta alpha beta chi delta epsilon eta gamma iota kappa
    lambda mu nu omega omicron phi pi psi rho sigma tau theta upsilon xi zeta varepsilon
    varkappa varphi varpi varrho varsigma vartheta
    Bmatrix Delta Gamma Lambda Leftrightarrow Omega Phi Pi Psi Rightarrow Sigma Theta Upsilon
    Vmatrix Xi binom bmatrix begin cases matrix pmatrix end gathered aligned alignedat array
    smallmatrix vmatrix
    acute bar breve check dot ddot dddot ddddot grave hat mathring overline tilde underline
    vec widehat widetilde
    boldsymbol mathbb mathbf mathcal mathfrak mathit mathrm mathsf mathtt operatorname text
    textrm textsf texttt
    cfrac dfrac frac sqrt tfrac dbinom tbinom
    coprod iint iiint int oint prod sum bigcap bigcup bigodot bigoplus bigotimes bigsqcup biguplus
    lim liminf limsup max min sup inf limits nolimits mathop
    Pr arg cos cosh cot coth csc deg det dim exp gcd hom ker lg ln log prime sec sin sinh tan tanh
    arccos arcsin arctan
    partial nabla ell hbar imath jmath infty emptyset varnothing Re Im wp aleph top bot
    approx asymp cong equiv ge geq geqslant gt le leq leqslant lt neq ne propto sim simeq
    subset subseteq supset supseteq sqsubseteq sqsupseteq in ni notin mid parallel perp models
    prec preceq succ succeq
    cap cdot circ cup diamond div mp odot ominus oplus oslash otimes pm setminus smallsetminus
    sqcap sqcup star times triangleleft triangleright uplus vee wedge wr
    forall exists nexists neg land lor implies iff therefore because
    gets leftarrow mapsto rightarrow to Leftarrow Longleftarrow Longleftrightarrow Longrightarrow
    longleftarrow longleftrightarrow longmapsto longrightarrow leftrightarrow hookleftarrow
    hookrightarrow uparrow downarrow updownarrow Uparrow Downarrow Updownarrow
    left right middle langle rangle lceil rceil lfloor rfloor lvert rvert lVert rVert vert Vert
    big Big bigg Bigg bigl bigr Bigl Bigr biggl biggr Biggl Biggr
    dots cdots ddots ldots vdots
    displaystyle scriptstyle scriptscriptstyle textstyle quad qquad
    overset underset overbrace underbrace stackrel substack
    mod bmod pmod pod
    tag boxed cancel
    """.split()
)
