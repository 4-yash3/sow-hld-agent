# SOW-HLD Agent

An agentic AI system that transforms a **Scope of Work (SOW) PDF into a High-Level Design (HLD)** and further develops that design into a **technology-specific implementation architecture**.

The project is designed to reduce the manual effort involved in understanding a Statement/Scope of Work, designing a solution architecture, selecting appropriate technologies, and documenting the reasoning behind those technology choices.

## 🚀 What Does It Do?

The SOW-HLD Agent takes a **Scope of Work PDF** as its primary input and processes it through multiple specialized agents and tools.

### Core Workflow

```text
Scope of Work (PDF)
        │
        ▼
┌─────────────────────┐
│   SOW Extraction    │
│  Text + Tables      │
└──────────┬──────────┘
           │
           ▼
┌─────────────────────┐
│    SOW Parser       │
│ Requirements &      │
│ Scope Understanding │
└──────────┬──────────┘
           │
           ▼
┌─────────────────────┐
│   Architect Agent   │
│ High-Level Design   │
└──────────┬──────────┘
           │
           ▼
   Architecture Design
           │
           ▼
┌─────────────────────┐
│ Diagram Renderer /  │
│ Document Compiler   │
└──────────┬──────────┘
           │
           ▼
   HLD Documentation
   + Architecture Diagram
```

The system is built around an **agentic workflow**, allowing different components of the system to handle specialized tasks such as SOW extraction, requirement analysis, architecture design, diagram generation, and document compilation.

---

# 🎯 Project Objectives

The project was developed in two major stages.

## 1. SOW → High-Level Design

The first objective is to build an agent that:

* Accepts a **Scope of Work PDF** as input.
* Extracts the relevant text and tabular information.
* Understands the requirements and scope of the proposed solution.
* Generates a **High-Level Design (HLD)** for the solution.
* Represents the architecture visually and/or through structured documentation.
* Supports output formats such as:

  * PNG
  * JPG
  * SVG
  * PPT/PPTX
  * DOCX

### Example

```text
SOW PDF
   │
   ▼
Requirement Extraction
   │
   ▼
Requirement Understanding
   │
   ▼
Solution Architecture
   │
   ├── Architecture Diagram
   ├── Components
   ├── Data Flow
   └── System Interactions
```

**Target Deadline:** 7 August

---

# 🏗️ 2. Detailed Implementation Architecture

After generating the High-Level Design, the second objective extends the agent with implementation-oriented architecture capabilities.

The system accepts:

```text
SOW PDF
     +
Solution Design
     │
     ▼
Detailed Implementation Architecture
```

For every architectural component, the agent identifies suitable technologies, including:

* Libraries
* Frameworks
* Tools
* Platforms
* Cloud services
* Databases
* Infrastructure components
* APIs and integrations

The architecture should also explain **why a particular technology was selected**.

### Technology Selection

For every component, the agent aims to provide:

| Component   | Technology             | Reason for Selection    | Alternative             |
| ----------- | ---------------------- | ----------------------- | ----------------------- |
| Component A | Recommended technology | Technical justification | Open-source/free option |
| Component B | Recommended technology | Technical justification | Open-source/free option |
| Component C | Recommended technology | Technical justification | Open-source/free option |

If the preferred technology is:

* Paid
* Proprietary
* Not freely available
* Not open source

the system should additionally identify a suitable **free or open-source alternative**.

The resulting architecture is intended to act as a **technical implementation guide** for developers.

**Target Deadline:** 14 August

---

# 🧠 Agent Architecture

The project uses multiple specialized components rather than relying on a single monolithic agent.

### Main Components

#### SOW Extractor

Extracts raw information from the incoming SOW PDF, including:

* Text
* Tables
* Relevant structured information

#### SOW Parser Agent

Processes the extracted SOW information and converts it into a structured representation of:

* Requirements
* Functional scope
* Non-functional requirements
* Constraints
* Actors
* Integrations
* Business requirements

#### Architect Agent

Uses the parsed requirements to design the solution architecture and identify:

* Major system components
* Services
* Data flows
* External integrations
* Communication patterns
* Architectural relationships

#### Diagram Renderer

Converts the generated architecture into a visual representation.

#### Document Compiler

Compiles the generated architecture and supporting information into structured documentation.

#### Implementation Agent

Extends the architecture process by identifying appropriate implementation technologies and providing technical justification for each architectural component.

---

# 🛠️ Technology Stack

The project is primarily built using:

* **Python**
* **LangGraph** for orchestrating the agentic workflow
* **LLM-based agents** for requirement understanding and architecture generation
* **PDF processing** for SOW extraction
* **Architecture/diagram generation tools**
* **DOCX/PPTX generation tools**
* **Agent-to-agent communication utilities**

---

# 📁 Project Structure

```text
sow-hld-agent/
│
├── agents/
│   ├── architect.py
│   ├── implementation_agent.py
│   └── sow_parser.py
│
├── flows/
│   ├── hld_generation_flow.py
│   └── state.py
│
├── tools/
│   ├── a2a_client.py
│   ├── agent_tools.py
│   ├── diagram_renderer.py
│   ├── doc_compiler.py
│   └── sow_extractor.py
│
├── main.py
├── router.py
├── requirements.txt
└── .gitignore
```

---

# 🔄 High-Level Processing Pipeline

```text
                    ┌──────────────────┐
                    │   SOW PDF Input  │
                    └────────┬─────────┘
                             │
                             ▼
                    ┌──────────────────┐
                    │  SOW Extraction  │
                    └────────┬─────────┘
                             │
                             ▼
                    ┌──────────────────┐
                    │   SOW Parser     │
                    └────────┬─────────┘
                             │
                             ▼
                    ┌──────────────────┐
                    │ Architect Agent  │
                    └────────┬─────────┘
                             │
                             ▼
                  ┌───────────────────────┐
                  │ High-Level Design     │
                  └───────────┬───────────┘
                              │
                 ┌────────────┴────────────┐
                 │                         │
                 ▼                         ▼
        Architecture Diagram       HLD Documentation
                 │                         │
                 └────────────┬────────────┘
                              │
                              ▼
                   ┌────────────────────┐
                   │ Implementation     │
                   │ Architecture       │
                   │ & Technology       │
                   │ Selection          │
                   └────────────────────┘
```

---

# 📌 Key Features

* 📄 **SOW PDF ingestion**
* 🔍 Automated requirement extraction
* 🧠 AI-powered requirement understanding
* 🏗️ Automated High-Level Design generation
* 📊 Architecture diagram generation
* 📝 Automated technical documentation
* 🧩 Component-level technology selection
* 💡 Technology selection reasoning
* 🆓 Free/open-source alternatives for proprietary technologies
* 🔄 Agentic workflow orchestration
* 🤖 Specialized AI agents for different stages of the workflow

---

# 🎯 Intended Outcome

The ultimate goal of the project is to create an automated pipeline capable of going from:

```text
Business Requirements
        ↓
Scope of Work
        ↓
High-Level Design
        ↓
Detailed Architecture
        ↓
Technology Selection
        ↓
Implementation Guidance
```

Instead of manually spending significant time translating an SOW into an architecture document, the SOW-HLD Agent provides an AI-assisted starting point that can be reviewed and refined by architects and developers.

#
