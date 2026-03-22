# AI Computing Power Industry Value Chain Mapping

## Executive Summary

This document provides a comprehensive mapping of the AI computing power (AI算力) industry value chain, covering upstream raw materials and equipment, midstream chip design and manufacturing, and downstream system integration and applications. The analysis identifies critical dependencies, bottlenecks, and key companies in each segment, with specific focus on both global and Chinese players.

### Value Chain Structure Overview

```
UPSTREAM (Materials & Equipment)
├── Raw Materials (Silicon, Rare Earths, Chemicals)
├── Semiconductor Equipment (Lithography, Etching, Deposition)
├── EDA Software (Design, Verification, Simulation)
└── IP Cores (Processor, Interface, Memory IP)

MIDSTREAM (Chip Production)
├── Chip Design (Fabless: GPU/NPU/TPU/ASIC)
├── Chip Manufacturing (Foundries: TSMC, Samsung, SMIC)
└── Packaging & Testing (OSAT: ASE, Amkor, JCET)

DOWNSTREAM (Systems & Applications)
├── System Integrators (Server Manufacturers)
├── Cloud Service Providers (AI Training/Inference)
├── Enterprise Customers (Internet, Finance, Auto)
└── End Applications (Training, Inference, Edge AI)
```

### Key Statistics
- **Total Market Size**: $600B+ semiconductor industry, $100B+ AI-specific
- **Critical Bottlenecks**: EUV lithography (ASML monopoly), advanced foundry (TSMC dominance)
- **Geographic Concentration**: Taiwan (foundry), Netherlands (EUV), USA (EDA/IP)
- **Chinese Self-Sufficiency Target**: 70% domestic production by 2025 (Made in China 2025)

## 1. Upstream Components

### 1.1 Raw Materials
**Critical Inputs:**
- **Silicon wafers**: High-purity monocrystalline silicon (99.9999999% purity)
- **Rare earth elements**: Gallium, germanium, indium for compound semiconductors
- **Specialty gases**: Argon, nitrogen, helium for fabrication processes
- **High-purity chemicals**: Photoresists, etchants, CMP slurries
- **Metals**: Copper, aluminum, gold for interconnects and packaging

**Key Global Companies:**
1. **Shin-Etsu Chemical** (Japan) - World's largest silicon wafer manufacturer
2. **SUMCO** (Japan) - Second largest silicon wafer producer
3. **GlobalWafers** (Taiwan) - Third largest wafer manufacturer
4. **Siltronic** (Germany) - European wafer leader
5. **Mitsubishi Materials** (Japan) - Specialty materials and chemicals

**Key Chinese Companies:**
1. **Zhonghuan Semiconductor** (Tianjin) - Leading Chinese wafer manufacturer
2. **National Silicon Industry Group (NSIG)** - State-backed wafer producer
3. **Jiangsu Zhongneng Polysilicon** - Polysilicon production
4. **GCL-Poly Energy** - Polysilicon and wafer production
5. **Tongwei Group** - Solar-grade polysilicon expansion into electronics

### 1.2 Semiconductor Equipment
**Critical Equipment Categories:**
- **Lithography**: EUV (Extreme Ultraviolet), DUV (Deep Ultraviolet)
- **Etching**: Plasma etchers, reactive ion etchers
- **Deposition**: CVD (Chemical Vapor Deposition), PVD (Physical Vapor Deposition)
- **Metrology**: Inspection, measurement, process control
- **Ion implantation**: Doping equipment
- **CMP**: Chemical Mechanical Planarization

**Key Global Companies:**
1. **ASML** (Netherlands) - Monopoly on EUV lithography (100% market share)
2. **Applied Materials** (USA) - Largest semiconductor equipment company
3. **Lam Research** (USA) - Etching and deposition equipment leader
4. **Tokyo Electron** (Japan) - Coating/developing, etching, deposition
5. **KLA Corporation** (USA) - Process control and yield management

**Key Chinese Companies:**
1. **NAURA Technology Group** - Largest Chinese semiconductor equipment maker
2. **Advanced Micro-Fabrication Equipment (AMEC)** - Etching and MOCVD equipment
3. **Shanghai Micro Electronics Equipment (SMEE)** - DUV lithography (90nm capability)
4. **Piotech** - Thin film deposition equipment
5. **Hwatsing Technology** - Cleaning and CMP equipment

### 1.3 EDA Software (Electronic Design Automation)
**Critical Software Categories:**
- **IC design**: Schematic capture, layout, simulation
- **Verification**: Formal verification, emulation, prototyping
- **Physical design**: Floor planning, placement, routing
- **Manufacturing preparation**: Mask data preparation, OPC (Optical Proximity Correction)

**Key Global Companies:**
1. **Synopsys** (USA) - Market leader in EDA and IP
2. **Cadence Design Systems** (USA) - Second largest EDA company
3. **Siemens EDA** (Germany) - Third largest (formerly Mentor Graphics)
4. **Ansys** (USA) - Simulation and analysis software
5. **Keysight Technologies** (USA) - Electronic design and test

**Key Chinese Companies:**
1. **Empyrean Technology** - Chinese EDA leader
2. **Primarius Technologies** - Simulation and verification tools
3. **X-Epic** - FPGA design tools
4. **S2C** - Prototyping and verification
5. **GigaDevice** - MCU design tools

### 1.4 IP Cores and Design Services
**Critical IP Categories:**
- **Processor cores**: CPU, GPU, NPU architectures
- **Interface IP**: USB, PCIe, DDR, Ethernet
- **Memory IP**: SRAM, ROM, Flash controllers
- **Analog IP**: PLLs, ADCs, DACs, SerDes

**Key Global Companies:**
1. **Arm Holdings** (UK/Japan) - Dominant CPU architecture (95%+ mobile market)
2. **Imagination Technologies** (UK) - GPU IP cores
3. **Synopsys** (USA) - Extensive IP portfolio
4. **Cadence** (USA) - Interface and memory IP
5. **CEVA** (Israel) - DSP and AI processor IP

**Key Chinese Companies:**
1. **Alibaba Pingtouge (T-Head)** - RISC-V processor IP
2. **C-SKY Microsystems** - Embedded CPU IP (acquired by Alibaba)
3. **VeriSilicon** - Chip design services and IP
4. **GigaDevice** - MCU and memory IP
5. **Unisoc** - Mobile communication IP

## 2. Midstream Components

### 2.1 Chip Design (Fabless)
**AI-Specific Chip Types:**
- **GPUs**: General-purpose AI training and inference (Nvidia, AMD)
- **NPUs**: Neural Processing Units for edge/mobile AI
- **TPUs**: Tensor Processing Units (Google)
- **AI ASICs**: Application-specific AI accelerators
- **FPGAs**: Field-programmable gate arrays for AI prototyping

**Key Global Companies:**
1. **Nvidia** (USA) - Dominant AI GPU market (>80% data center AI training)
2. **AMD** (USA) - Second largest GPU manufacturer
3. **Intel** (USA) - CPU with integrated AI accelerators (VPU)
4. **Qualcomm** (USA) - Mobile AI processors (Snapdragon)
5. **Apple** (USA) - Apple Silicon with Neural Engine

**Key Chinese Companies:**
1. **HiSilicon** (Huawei) - Kirin processors with Da Vinci NPU
2. **Cambricon** - AI accelerator chips (cloud and edge)
3. **Horizon Robotics** - Automotive AI processors
4. **Iluvatar CoreX** - AI training chips
5. **Enflame Technology** - AI training accelerators

### 2.2 Chip Manufacturing (Foundries)
**Process Technology Nodes:**
- **Advanced nodes**: 3nm, 5nm, 7nm (TSMC, Samsung)
- **Mature nodes**: 14nm, 28nm, 40nm (SMIC, UMC, GlobalFoundries)
- **Specialty processes**: RF, analog, power, MEMS

**Key Global Foundries:**
1. **TSMC** (Taiwan) - World's largest foundry (>50% market share)
2. **Samsung Foundry** (South Korea) - Second largest, competing at advanced nodes
3. **GlobalFoundries** (USA) - Largest Western foundry (mature nodes)
4. **UMC** (Taiwan) - Second largest Taiwanese foundry
5. **Intel Foundry Services** (USA) - New entrant to foundry business

**Key Chinese Foundries:**
1. **SMIC** (Semiconductor Manufacturing International Corp) - Largest Chinese foundry
2. **Hua Hong Semiconductor** - Second largest Chinese foundry
3. **Nexchip** - DRAM-focused foundry
4. **Wingtech** - Assembly and test with some manufacturing
5. **Silan Microelectronics** - IDM with foundry services

### 2.3 Packaging and Testing (OSAT)
**Advanced Packaging Technologies:**
- **2.5D/3D packaging**: Chip-on-wafer, wafer-on-wafer
- **Fan-out**: InFO (Integrated Fan-Out)
- **System-in-Package (SiP)**: Heterogeneous integration
- **Chiplet-based packaging**: Advanced interconnect technologies

**Key Global OSAT Companies:**
1. **ASE Group** (Taiwan) - World's largest OSAT
2. **Amkor Technology** (USA) - Second largest OSAT
3. **JCET** (China) - Third largest OSAT
4. **Powertech Technology** (Taiwan) - Memory packaging specialist
5. **ChipMOS** (Taiwan) - Display driver and memory testing

**Key Chinese OSAT Companies:**
1. **JCET Group** - Largest Chinese OSAT (global #3)
2. **Tongfu Microelectronics** - Second largest Chinese OSAT
3. **Huatian Technology** - Third largest Chinese OSAT
4. **Nepes** - Advanced packaging services
5. **Chipmore Technology** - Testing and packaging

## 3. Downstream Components

### 3.1 System Integrators (Server Manufacturers)
**AI Server Specializations:**
- **GPU-accelerated servers**: Nvidia DGX, HGX systems
- **AI training clusters**: Large-scale systems for model training
- **Edge AI servers**: Compact systems for inference at edge
- **Liquid-cooled servers**: High-density AI computing

**Key Global System Integrators:**
1. **Dell Technologies** (USA) - Largest server vendor
2. **HPE** (USA) - Second largest server vendor
3. **Inspur** (China) - Third largest server vendor globally
4. **Lenovo** (China) - Fourth largest server vendor
5. **Super Micro Computer** (USA) - White-label server specialist

**Key Chinese System Integrators:**
1. **Inspur Information** - World's largest AI server supplier
2. **H3C** (HPE joint venture) - Enterprise servers and networking
3. **Sugon** (Dawning Information) - HPC and AI systems
4. **Huawei** - Kunpeng and Ascend-based servers
5. **Lenovo** - Global server business with strong China presence

### 3.2 Cloud Service Providers
**AI Cloud Services:**
- **AI training platforms**: Pre-configured environments for model training
- **Inference services**: Real-time AI model serving
- **AI-as-a-Service**: Pre-trained models and APIs
- **MLOps platforms**: End-to-end machine learning operations

**Key Global Cloud Providers:**
1. **Amazon Web Services (AWS)** - Largest cloud provider with AI services (SageMaker)
2. **Microsoft Azure** - Second largest with Azure AI and OpenAI partnership
3. **Google Cloud Platform** - Third largest with TPU and Vertex AI
4. **IBM Cloud** - Enterprise AI with Watson
5. **Oracle Cloud** - Database-focused AI services

**Key Chinese Cloud Providers:**
1. **Alibaba Cloud** - Largest Chinese cloud provider
2. **Tencent Cloud** - Second largest Chinese cloud provider
3. **Huawei Cloud** - Fastest growing Chinese cloud
4. **Baidu AI Cloud** - AI-focused cloud services
5. **Kingsoft Cloud** - Gaming and enterprise cloud

### 3.3 Enterprise Customers
**Major AI Computing Consumers:**
- **Internet companies**: Search, social media, e-commerce
- **Financial services**: Fraud detection, algorithmic trading
- **Healthcare**: Medical imaging, drug discovery
- **Automotive**: Autonomous driving, ADAS
- **Manufacturing**: Quality control, predictive maintenance

**Key Global Enterprise Customers:**
1. **Meta** (Facebook) - Largest consumer of AI chips for recommendation systems
2. **Microsoft** - AI integration across products (Office, Windows, Azure)
3. **Google** - Search, YouTube, AI research (DeepMind)
4. **Tesla** - Full Self-Driving and Dojo AI training
5. **OpenAI** - Large language model training and inference

**Key Chinese Enterprise Customers:**
1. **ByteDance** (TikTok/Douyin) - Video recommendation algorithms
2. **Tencent** - Gaming, social media, fintech
3. **Alibaba** - E-commerce, cloud, fintech
4. **Baidu** - Search, autonomous driving (Apollo)
5. **iFlytek** - Speech recognition and AI applications

### 3.4 End Applications
**AI Computing Applications:**
- **AI training**: Large language models, computer vision models
- **AI inference**: Real-time processing of trained models
- **Edge computing**: IoT devices, smartphones, autonomous vehicles
- **Scientific computing**: Climate modeling, protein folding, materials science

## 4. Key Dependencies and Bottlenecks

### 4.1 Critical Supply Chain Bottlenecks

**1. EUV Lithography Monopoly:**
- **Single point of failure**: ASML has 100% market share in EUV lithography
- **Export controls**: US restrictions on EUV sales to China
- **Complex supply chain**: 100,000+ components from 5,000+ suppliers
- **Geographic concentration**: Critical suppliers in Netherlands, Germany, USA

**2. Advanced Process Node Concentration:**
- **Taiwan dominance**: TSMC produces ~90% of world's advanced chips (<7nm)
- **Geopolitical risk**: Taiwan Strait tensions create supply chain vulnerability
- **Limited alternatives**: Only Samsung and Intel can compete at advanced nodes

**3. EDA Software Dependency:**
- **US dominance**: Synopsys, Cadence, Siemens control ~85% of EDA market
- **Export restrictions**: US bans advanced EDA tools to China
- **High switching costs**: Years of accumulated IP and ecosystem lock-in

**4. IP Architecture Control:**
- **Arm architecture dominance**: >95% of mobile processors use Arm
- **x86 lock-in**: Intel/AMD control server and PC markets
- **RISC-V emergence**: Open alternative gaining traction but ecosystem immature

**5. Raw Material Concentration:**
- **Silicon purification**: Japan controls ~60% of high-purity silicon
- **Rare earth processing**: China controls ~80% of rare earth processing
- **Specialty gases**: Limited suppliers for high-purity process gases

### 4.2 Single Points of Failure

**1. TSMC's Advanced Node Production:**
- Location: Taiwan (geopolitical risk)
- Capacity: ~90% of world's <7nm chips
- Customers: Apple, Nvidia, AMD, Qualcomm

**2. ASML's EUV Systems:**
- Monopoly: 100% of EUV lithography market
- Production rate: ~40 systems/year
- Lead time: 18-24 months

**3. Applied Materials/Lam Research:**
- Critical equipment: Etching, deposition, CMP
- US export controls: Restrictions on China sales
- Limited alternatives: Chinese equipment 2-3 generations behind

**4. Synopsys/Cadence EDA:**
- Market share: ~85% combined
- Ecosystem lock-in: Decades of IP accumulation
- No viable Chinese alternatives for advanced nodes

### 4.3 Geopolitical Chokepoints

**1. Taiwan Strait:**
- 90% of advanced chips pass through or are made in Taiwan
- Major shipping lanes for semiconductor materials and equipment
- Potential blockade scenario would cripple global electronics

**2. Malacca Strait:**
- 40% of global trade passes through
- Critical for raw material transport (silicon, rare earths)
- Alternative routes add significant time and cost

**3. US Export Controls:**
- BIS Entity List restrictions on Chinese companies
- Foreign Direct Product Rule extension
- Multilateral controls with Japan and Netherlands

## 5. Company Mapping by Segment

### 5.1 Global vs Chinese Company Comparison

| Segment | Global Leaders | Chinese Counterparts | Technology Gap | Key Constraints |
|---------|---------------|---------------------|----------------|-----------------|
| **EDA Software** | Synopsys, Cadence, Siemens | Empyrean, Primarius | 2-3 generations | US export controls, ecosystem lock-in |
| **Lithography** | ASML (EUV), Nikon, Canon | SMEE (DUV only) | 3+ generations | EUV technology blockade, precision optics |
| **Process Equipment** | Applied Materials, Lam Research | NAURA, AMEC | 2-3 generations | Advanced process know-how, materials science |
| **Foundry** | TSMC, Samsung, Intel | SMIC, Hua Hong | 2-3 nodes behind | EUV access, process integration expertise |
| **Fabless Design** | Nvidia, AMD, Qualcomm | HiSilicon, Cambricon | 1-2 generations | Advanced node access, software ecosystem |
| **OSAT** | ASE, Amkor | JCET, Tongfu | 0.5-1 generation | Advanced packaging equipment, materials |
| **Materials** | Shin-Etsu, SUMCO | Zhonghuan, NSIG | 1-2 generations | Purification technology, defect control |

### 5.2 Technology Gap Analysis by Node

**Current State (2025):**
- **Global leaders**: 3nm mass production (TSMC, Samsung), 2nm development
- **Chinese leaders**: 7nm mass production (SMIC N+2), 5nm development
- **Gap**: Approximately 3-4 years in process technology

**Critical Technology Dependencies:**
1. **EUV Lithography**: Chinese DUV multi-patterning vs global EUV single exposure
2. **Advanced Packaging**: Chinese developing 2.5D/3D but lagging in CoWoS/InFO
3. **Materials**: High-purity silicon and specialty chemicals import dependent
4. **Metrology**: Process control and yield management tools lagging

**Chinese Progress Despite Sanctions:**
- **7nm breakthrough**: SMIC N+2 process without EUV (2023)
- **Domestic equipment**: 28nm equipment ecosystem nearly complete
- **RISC-V ecosystem**: Rapid development as Arm alternative
- **Government funding**: $150B+ committed through Big Fund phases

### 5.2 Strategic Relationships and Dependencies

**1. Nvidia-TSMC Relationship:**
- **Nature**: Customer-foundry
- **Dependency**: Nvidia designs depend on TSMC's advanced packaging (CoWoS)
- **Volume**: TSMC produces 100% of Nvidia's advanced GPUs
- **Risk**: Single-source dependency on Taiwan-based production

**2. Apple-TSMC Relationship:**
- **Nature**: Exclusive foundry partnership
- **Dependency**: Apple Silicon entirely manufactured by TSMC
- **Volume**: TSMC's largest customer (~25% of revenue)
- **Advanced nodes**: First to adopt new process technologies

**3. Huawei-SMIC Relationship:**
- **Nature**: Strategic partnership for domestic supply
- **Dependency**: Huawei designs manufactured by SMIC despite US sanctions
- **Breakthrough**: 7nm Kirin 9000S chip demonstrated domestic capability
- **Government support**: Both companies receive state funding and protection

**4. ASML-TSMC/Samsung Relationship:**
- **Nature**: Equipment supplier-customer
- **Dependency**: TSMC/Samsung depend on ASML for EUV systems
- **Co-development**: Joint development of next-generation EUV
- **Installation base**: TSMC has largest number of EUV systems

## 6. Relationship Types and Evidence

### 6.1 Supplier-Customer Relationships

**Evidence:**
1. **TSMC Customer Concentration**: Apple (25%), Nvidia (11%), AMD (10%), Qualcomm (8%)
2. **ASML Customer Base**: TSMC (46% of systems), Samsung (29%), Intel (15%)
3. **Applied Materials Customer Mix**: Foundries (75%), IDMs (25%)
4. **Nvidia Supplier Base**: TSMC (manufacturing), Samsung (memory), ASE (packaging)

### 6.2 Technology Licensing Relationships

**Evidence:**
1. **Arm Licensing Model**: Royalty-based licensing to Apple, Qualcomm, Samsung, Huawei
2. **x86 Cross-Licensing**: Intel-AMD cross-license agreement (expired 2024)
3. **RISC-V Foundation**: Open-standard architecture with Chinese participation (Alibaba, Huawei)
4. **EDA Tool Licensing**: Annual subscription model with maintenance fees

### 6.3 Joint Ventures and Strategic Partnerships

**Evidence:**
1. **Intel-TSMC Partnership**: Intel outsourcing to TSMC for GPU tiles (Ponte Vecchio)
2. **Samsung-AMD Partnership**: AMD RDNA graphics IP in Samsung Exynos
3. **Huawei-SMIC Collaboration**: Joint development of 7nm process without EUV
4. **Alibaba-Pingtouge**: In-house chip design division using RISC-V

### 6.4 Government-Industry Relationships

**Evidence:**
1. **China's Big Fund**: $50+ billion invested in semiconductor industry since 2014
2. **US CHIPS Act**: $52 billion for domestic semiconductor manufacturing
3. **EU Chips Act**: €43 billion for European semiconductor ecosystem
4. **Japan Subsidies**: $6.8 billion for TSMC/Rapidus fabs in Japan

## 7. Value Chain Analysis

### 7.1 Profit Distribution Across Value Chain

**Typical Value Distribution:**
1. **EDA/IP (15-20%)**: High margins (30-40%), recurring revenue
2. **Equipment (10-15%)**: High R&D, cyclical demand
3. **Foundry (25-30%)**: Capital intensive, economies of scale critical
4. **Fabless Design (30-35%)**: Highest value capture for successful designs
5. **OSAT (5-10%)**: Lower margins, labor intensive
6. **System Integration (10-15%)**: Volume business with thin margins

### 7.2 Capital Intensity by Segment

**R&D and Capex Requirements:**
1. **EDA Software**: High R&D (20-30% of revenue), low capex
2. **Equipment Manufacturing**: Very high R&D (15-20%), moderate capex
3. **Foundries**: Moderate R&D (10-15%), extremely high capex ($20B+ per fab)
4. **Fabless Design**: High R&D (15-25%), low capex
5. **OSAT**: Low R&D (5-10%), high capex for advanced packaging

### 7.3 Barriers to Entry

**By Segment:**
1. **EDA**: Very high (decades of IP accumulation, ecosystem lock-in)
2. **Equipment**: Extremely high (precision engineering, customer validation)
3. **Foundry**: Extremely high ($20B+ for advanced node fab)
4. **Fabless Design**: High (design expertise, ecosystem access)
5. **OSAT**: Moderate (capital intensive but less IP-dependent)

## 8. Future Trends and Implications

### 8.1 Technology Trends

**1. Chiplet Architecture:**
- Modular design with heterogeneous integration
- Reduces design complexity and improves yield
- Enables mixing process nodes and technologies
- **Key players**: AMD, Intel, Chinese companies developing alternatives

**2. Advanced Packaging:**
- 2.5D/3D integration becoming mainstream
- CoWoS, InFO, EMIB technologies
- Critical for AI chip performance
- **Bottleneck**: Limited advanced packaging capacity

**3. RISC-V Adoption:**
- Open architecture gaining traction in China
- Alibaba T-Head developing high-performance RISC-V cores
- Potential alternative to Arm/x86 dependency
- **Challenge**: Immature software ecosystem

**4. Photonic Computing:**
- Optical interconnects for chip-to-chip communication
- Potential for lower power, higher bandwidth
- Early research stage, 5-10 year horizon
- **Chinese research**: Significant investment in photonic chips

### 8.2 Geopolitical Implications

**1. Decoupling and Resilience:**
- US/China technological deceleration accelerating
- Dual supply chains emerging
- Increased inventory buffers and redundancy
- Higher costs passed to consumers

**2. Regionalization:**
- US rebuilding domestic manufacturing (Intel, TSMC Arizona)
- Europe developing indigenous capability (STMicro, Infineon)
- China pursuing self-sufficiency despite efficiency loss
- Southeast Asia gaining importance (Malaysia, Vietnam)

**3. Export Control Evolution:**
- Expanding from equipment to materials and software
- Multilateral coordination (US-Japan-Netherlands)
- Focus on "chokepoint" technologies (EUV, advanced EDA)
- Dynamic lists adapting to technological progress

### 8.3 Market Structure Evolution

**1. Vertical Integration:**
- Apple moving to in-house silicon
- Google developing TPUs
- Amazon developing Trainium/Inferentia
- Huawei developing full stack (chip to cloud)

**2. Specialization vs Integration:**
- Foundry model under pressure from geopolitical risks
- IDM model resurgence (Intel, Samsung)
- Hybrid models emerging (TSMC with advanced packaging)
- Chinese forced integration due to sanctions

**3. New Business Models:**
- Chip-as-a-service emerging
- Design platform ecosystems
- Open hardware movements (RISC-V)
- Sovereign chip initiatives

## 9. Recommendations for Industry Participants

### 9.1 For Global Companies

**1. Diversify Supply Chains:**
- Multiple geographic sources for critical components
- Inventory buffers for geopolitical disruptions
- Alternative technologies and architectures

**2. Navigate Geopolitics:**
- Separate China and non-China product lines
- Compliance with evolving export controls
- Government relations and lobbying

**3. Invest in Next-Generation Technologies:**
- Quantum computing, photonics, neuromorphic
- Advanced packaging and chiplet architectures
- Software-defined hardware

### 9.2 For Chinese Companies

**1. Pursue Technological Independence:**
- Focus on mature node optimization
- Develop domestic equipment and materials
- Build RISC-V ecosystem
- Government funding and protection

**2. Leverage Scale Advantages:**
- Domestic market as testing ground
- Cost leadership in mature nodes
- System-level integration capabilities
- Government procurement support

**3. International Collaboration (Where Possible):**
- Partnerships with non-US allies
- Academic and research collaborations
- Standards participation (RISC-V, Open Compute)
- Southeast Asian manufacturing bases

### 9.3 For Investors and Policymakers

**1. Identify Strategic Investments:**
- Bottleneck technologies (equipment, materials)
- Alternative architectures (RISC-V, open hardware)
- Regional manufacturing capacity
- Workforce development

**2. Policy Framework Development:**
- Export control coordination
- Intellectual property protection
- Research funding allocation
- International standards participation

**3. Risk Management:**
- Supply chain mapping and monitoring
- Scenario planning for disruptions
- Redundancy and resilience planning
- Insurance and financial instruments

## 10. Conclusion

The AI computing power value chain represents one of the most complex and strategically important industrial ecosystems in the world. Its structure reflects decades of globalization, specialization, and technological evolution, but now faces unprecedented pressures from geopolitical competition, technological disruption, and supply chain fragility.

**Key Takeaways:**

1. **Extreme Concentration**: Critical bottlenecks at EUV lithography, advanced foundry, and EDA software create systemic vulnerabilities.

2. **Geopolitical Fragmentation**: US-China decoupling is forcing duplication of supply chains at enormous cost.

3. **Chinese Progress Despite Sanctions**: Domestic capabilities advancing rapidly in mature nodes and system integration, though lagging in cutting-edge technologies.

4. **Structural Evolution**: Vertical integration, chiplet architectures, and open hardware movements reshaping traditional value chain.

5. **Strategic Importance**: Control over AI computing infrastructure increasingly viewed as national security imperative.

The future of the AI computing power industry will be shaped by the tension between economic efficiency (global specialization) and strategic resilience (regional self-sufficiency). Companies and countries that successfully navigate this tension while investing in next-generation technologies will shape the computing landscape for decades to come.

---

*Document prepared by Industry Research Lab Value-Chain Mapping Team*
*Last updated: March 2025*
*Sources: Industry reports, company filings, academic research, trade publications*