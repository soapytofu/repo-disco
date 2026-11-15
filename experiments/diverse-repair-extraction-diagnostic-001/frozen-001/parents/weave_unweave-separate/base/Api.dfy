include "Kernel.dfy"
module Api {
  export Public provides K, Empty, Project
  import K = Kernel`Internal
  lemma Empty(s: seq<int>, t: seq<int>)
    requires |s| == 0 && |t| == 0
    ensures K.Weave(s,t) == [] && K.Left([]) == [] && K.Right([]) == []
  { reveal K.Weave(); reveal K.Left(); reveal K.Right(); }
  lemma Project(x: int, y: int, u: seq<int>)
    ensures K.Left([x,y]+u) == [x]+K.Left(u)
    ensures K.Right([x,y]+u) == [y]+K.Right(u)
  { reveal K.Left(); reveal K.Right(); }
}
