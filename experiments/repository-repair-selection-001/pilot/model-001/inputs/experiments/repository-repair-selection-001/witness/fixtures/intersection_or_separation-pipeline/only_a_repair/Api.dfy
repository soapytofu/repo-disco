include "Kernel.dfy"
module Api {
  export Proof provides K, Witness, Gap
  export Clients provides K, Choose
  export Hidden provides K, DirectWitness
  import K = Kernel`Internal
  lemma Witness(a: int, b: int, c: int, d: int, w: int)
    requires K.LeftFact(a,b,w) && K.RightFact(c,d,w)
    ensures K.Decided(a,b,c,d)
  {
    reveal K.LeftFact(); reveal K.RightFact(); reveal K.Valid();
    assert K.Valid(a,b,c,d,0,w);
    reveal K.Decided();
    assert exists tag: int, point: int {:trigger K.Valid(a,b,c,d,tag,point)} :: K.Valid(a,b,c,d,tag,point);
  }
  lemma Gap(a: int, b: int, c: int, d: int, kind: int)
    requires (kind == -1 && K.LeftGap(b,c)) || (kind == 1 && K.RightGap(d,a))
    ensures K.Decided(a,b,c,d)
  {
    reveal K.LeftGap(); reveal K.RightGap(); reveal K.Valid();
    assert K.Valid(a,b,c,d,kind,0);
    reveal K.Decided();
    assert exists tag: int, point: int {:trigger K.Valid(a,b,c,d,tag,point)} :: K.Valid(a,b,c,d,tag,point);
  }
  lemma Choose(a: int, b: int, c: int, d: int) returns (kind: int, w: int)
    requires a <= b && c <= d
    requires K.Decided(a,b,c,d)
    ensures kind == -1 || kind == 0 || kind == 1
    ensures kind == 0 ==> a <= w <= b && c <= w <= d
    ensures (kind == 0) == (a <= d && c <= b)
    ensures (kind == -1) == (b < c)
    ensures (kind == 1) == (d < a)
  {
    reveal K.Decided();
    kind, w :| K.Valid(a,b,c,d,kind,w);
    reveal K.Valid();
  }
  lemma DirectWitness(a: int, b: int, c: int, d: int, w: int)
    requires a <= w <= b && c <= w <= d
    ensures K.Decided(a,b,c,d)
  {
    reveal K.Valid(); assert K.Valid(a,b,c,d,0,w);
    reveal K.Decided();
    assert exists tag: int, point: int {:trigger K.Valid(a,b,c,d,tag,point)} :: K.Valid(a,b,c,d,tag,point);
  }
}
