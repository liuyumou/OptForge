// Exact flat-expert market via a signed-network double cover.
// Capacities use unsigned 128-bit integers; costs/potentials are integral.
// No floating-point optimization, no delegation of the original LP.
#include <algorithm>
#include <chrono>
#include <cstdint>
#include <deque>
#include <limits>
#include <queue>
#include <stdexcept>
#include <utility>
#include <vector>

using U = unsigned __int128;
using I = std::int64_t;
static constexpr I INF = I(1)<<60;
struct Edge { int to, reverse; U capacity; I cost; };
struct Stop { int code; };
struct Flow {
    std::vector<std::vector<Edge>> g;
    std::vector<I> potential, distance;
    std::vector<int> level, current;
    std::chrono::steady_clock::time_point deadline;
    std::uint64_t scans=0, max_scans, augmentations=0, phases=0;
    explicit Flow(int n, std::uint64_t nanoseconds, std::uint64_t bound):
        g(n), potential(n,0), distance(n), level(n), current(n),
        deadline(std::chrono::steady_clock::now()+std::chrono::nanoseconds(nanoseconds)), max_scans(bound) {}
    void tick() {
        if(++scans>max_scans)throw Stop{2};
        if((scans&4095)==0 && std::chrono::steady_clock::now()>deadline)throw Stop{1};
    }
    static I number(__int128 x) {
        if(x<=-INF/2 || x>=INF/2)throw Stop{3};
        return I(x);
    }
    int add(int u,int v,U cap,I cost) {
        int index=int(g[u].size()), reverse=int(g[v].size());
        g[u].push_back({v,reverse,cap,cost});
        g[v].push_back({u,index,0,-cost});return index;
    }
    I reduced(int u,const Edge& e) { return number(__int128(e.cost)+potential[u]-potential[e.to]); }
    void initialize() {
        std::deque<int> queue;
        std::vector<bool> queued(g.size(),true);
        std::vector<int> visits(g.size(),0);
        for(int i=0;i<int(g.size());++i)queue.push_back(i);
        while(!queue.empty()) {
            int u=queue.front();queue.pop_front();queued[u]=false;
            for(const auto& e:g[u]) {tick();if(!e.capacity)continue;
                I value=number(__int128(potential[u])+e.cost);
                if(value<potential[e.to]) {
                    potential[e.to]=value;
                    if(!queued[e.to]) {queue.push_back(e.to);queued[e.to]=true;
                        if(++visits[e.to]>int(g.size()))throw Stop{4};}
                }
            }
        }
    }
    void shortest(int source,int vertices) {
        std::fill(distance.begin(),distance.end(),INF);
        using Pair=std::pair<I,int>;
        std::priority_queue<Pair,std::vector<Pair>,std::greater<Pair>> heap;
        distance[source]=0;heap.push({0,source});
        while(!heap.empty()) {
            auto [d,u]=heap.top();heap.pop();if(d!=distance[u])continue;
            for(const auto& e:g[u]) {tick();if(!e.capacity||e.to>=vertices)continue;
                I cost=reduced(u,e);if(cost<0)throw Stop{5};
                I candidate=number(__int128(d)+cost);
                if(candidate<distance[e.to]){distance[e.to]=candidate;heap.push({candidate,e.to});}
            }
        }
    }
    bool levels(int source,int sink) {
        std::fill(level.begin(),level.end(),-1);level[source]=0;
        std::vector<int> queue{source};
        for(std::size_t at=0;at<queue.size();++at) {
            int u=queue[at];
            for(const auto& e:g[u]) {tick();
                if(e.capacity && level[e.to]<0 && reduced(u,e)==0) {
                    level[e.to]=level[u]+1;
                    if(level[e.to]>2048)throw Stop{6};
                    queue.push_back(e.to);
                }
            }
        }
        std::fill(current.begin(),current.end(),0);
        return level[sink]>=0;
    }
    U send(int u,int sink,U amount) {
        if(u==sink)return amount;
        for(int& k=current[u];k<int(g[u].size());++k) {
            tick();auto& e=g[u][k];
            if(!e.capacity || level[e.to]!=level[u]+1 || reduced(u,e)!=0)continue;
            U sent=send(e.to,sink,std::min(amount,e.capacity));
            if(sent) {e.capacity-=sent;g[e.to][e.reverse].capacity+=sent;return sent;}
        }
        return 0;
    }
    void solve(int source,int sink,U required) {
        initialize();
        while(required) {
            ++phases;shortest(source,int(g.size()));
            if(distance[sink]==INF)throw Stop{7};
            for(int v=0;v<int(g.size());++v)
                potential[v]=number(__int128(potential[v])+std::min(distance[v],distance[sink]));
            while(required && levels(source,sink)) {
                while(required) {
                    U sent=send(source,sink,required);if(!sent)break;
                    required-=sent;++augmentations;
                }
            }
        }
    }
    void lexicographic(int coordinates,int vertices) {
        for(int i=0;i<coordinates;++i) {
            int a=2+2*i,b=1+2*i; // minimize (pi_minus-pi_plus)/2
            shortest(a,vertices);
            I d=distance[b];if(d==INF)throw Stop{8};
            I original=number(__int128(d)-potential[a]+potential[b]);
            for(int v=0;v<vertices;++v) if(distance[v]<d)
                potential[v]=number(__int128(potential[v])+distance[v]-d);
            // This is a potential constraint, added only after the flow is fixed.
            add(b,a,U(1),-original);
        }
    }
};

extern "C" int sp_market(int n,int experts,int entries,const int* offsets,
    const int* coordinate,const int* sign,const I* demand,
    const std::uint64_t* weight_low,const std::uint64_t* weight_high,
    std::uint64_t nanoseconds,std::uint64_t max_scans,I* price_twice,
    std::uint64_t* flow_low,std::uint64_t* flow_high,std::uint64_t* metrics) {
    if(n<1 || experts<1 || experts>65536 || n>10000 || entries<experts || entries>5*experts
       || !offsets||!coordinate||!sign||!demand||!weight_low||!weight_high
       ||!price_twice||!flow_low||!flow_high||!metrics||!nanoseconds||!max_scans)return -1;
    if(offsets[0]!=0||offsets[experts]!=entries)return -1;
    for(int e=0;e<experts;++e)if(offsets[e+1]<=offsets[e]||offsets[e+1]-offsets[e]>5)return -1;
    try {
        int vertices=1+2*n+2*experts,source=vertices,sink=vertices+1;
        Flow network(vertices+2,nanoseconds,max_scans);
        U total=0;
        std::vector<U> weights(experts);
        for(int e=0;e<experts;++e) {
            weights[e]=U(weight_low[e])|(U(weight_high[e])<<64);
            if(!weights[e]||weights[e]>(U(1)<<120))return -2;
            total+=weights[e];if(total>(U(1)<<124))return -2;
        }
        U infinite=total+1;
        std::vector<std::pair<int,int>> arcs;
        arcs.reserve(2*entries);
        for(int e=0;e<experts;++e) {
            int plus=1+2*n+2*e,minus=plus+1;
            network.add(source,plus,weights[e],0);network.add(minus,sink,weights[e],0);
            bool outside=false;
            for(int j=offsets[e];j<offsets[e+1];++j) {
                int to,from;
                if(coordinate[j]==-1) {
                    if(demand[j]!=0||sign[j]!=0||outside)return -1;
                    outside=true;to=from=0;
                } else {
                    if(coordinate[j]<0||coordinate[j]>=n||(sign[j]!=1&&sign[j]!=-1))return -1;
                    to=1+2*coordinate[j]+(sign[j]<0);from=1+2*coordinate[j]+(sign[j]>0);
                }
                if(__int128(demand[j])*vertices>INF/32 || __int128(demand[j])*vertices<-INF/32)return -2;
                arcs.push_back({plus,network.add(plus,to,infinite,-demand[j])});
                arcs.push_back({from,network.add(from,minus,infinite,-demand[j])});
            }
            if(!outside)return -1;
        }
        network.solve(source,sink,total);
        network.lexicographic(n,vertices);
        for(int i=0;i<n;++i)price_twice[i]=network.potential[2+2*i]-network.potential[1+2*i];
        for(int j=0;j<2*entries;++j) {
            auto [u,k]=arcs[j];U f=infinite-network.g[u][k].capacity;
            flow_low[j]=std::uint64_t(f);flow_high[j]=std::uint64_t(f>>64);
        }
        metrics[0]=network.scans;metrics[1]=network.augmentations;metrics[2]=network.phases;
        return 0;
    }catch(const Stop& stop){return stop.code;}
    catch(const std::bad_alloc&){return 9;}
    catch(...){return 10;}
}
