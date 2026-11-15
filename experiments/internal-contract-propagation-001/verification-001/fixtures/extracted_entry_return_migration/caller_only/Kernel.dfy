module Kernel {
  function Erase(m: map<int,int>, key: int): map<int,int> {
    map x | x in m && x != key :: m[x]
  }
  function Entry(m: map<int,int>, key: int): map<int,int> {
    map x | x in m && x == key :: m[x]
  }
  function Exclude(m: map<int,int>, patch: map<int,int>): map<int,int> {
    map x | x in m && x !in patch :: m[x]
  }
}
