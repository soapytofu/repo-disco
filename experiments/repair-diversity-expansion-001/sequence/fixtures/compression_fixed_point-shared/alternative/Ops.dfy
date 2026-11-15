include "Kernel.dfy"
module Ops {
  export Public provides K, Base, TailInvariant, Boundary, Keep
  export Internal provides K, Base, TailInvariant, Boundary, Keep, Drop
  import K = Kernel`Internal
  lemma Base(s: seq<int>)
    requires |s| < 2
    ensures K.Compress(s) == s
  { reveal K.Compress(); }
  lemma TailInvariant(s: seq<int>)
    requires K.Clean(s) && 2 <= |s|
    ensures K.Clean(s[1..])
  { reveal K.Clean(); }
  lemma Boundary(s: seq<int>)
    requires K.Clean(s) && 2 <= |s|
    ensures s[0] != s[1]
  { reveal K.Clean(); }
  lemma Keep(s: seq<int>)
    requires 2 <= |s| && s[0] != s[1]
    ensures K.Compress(s) == [s[0]] + K.Compress(s[1..])
  { reveal K.Compress(); }
  lemma Drop(s: seq<int>)
    requires 2 <= |s| && s[0] == s[1]
    ensures K.Compress(s) == K.Compress(s[1..])
  { reveal K.Compress(); }
}
