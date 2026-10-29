include "Kernel.dfy"
module Stage2 {
  export Public provides K, Join
  import K = Kernel`Internal
  lemma Join(a: int, b: int, c: int, d: int, w: int)
    requires K.LeftFact(a,b,w) && K.RightFact(c,d,w)
    ensures K.Joined(a,b,c,d,w)
  { reveal K.Joined(); }
}
