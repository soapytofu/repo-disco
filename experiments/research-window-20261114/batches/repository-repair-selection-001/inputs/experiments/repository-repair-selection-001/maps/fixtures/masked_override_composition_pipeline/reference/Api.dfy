module Api {
  export Public provides Equal
  lemma Equal(left: map<int,int>, right: map<int,int>)
    requires left.Keys == right.Keys
    requires forall x :: x in left ==> x in right && left[x] == right[x]
    ensures left == right
  { }
}
