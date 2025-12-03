from wholecell.sim.simulation import Simulation

# States
from wholecell.states.bulk_molecules import BulkMolecules
from wholecell.states.unique_molecules import UniqueMolecules
from wholecell.states.local_environment import LocalEnvironment

# Processes
from models.ecoli.processes.complexation import Complexation
from models.ecoli.processes.metabolism import Metabolism
from models.ecoli.processes.rna_degradation import RnaDegradation
from models.ecoli.processes.rna_maturation import RnaMaturation
from models.ecoli.processes.cell_division import CellDivision
from models.ecoli.processes.chromosome_replication import ChromosomeReplication
from models.ecoli.processes.chromosome_structure import ChromosomeStructure
from models.ecoli.processes.polypeptide_initiation import PolypeptideInitiation
from models.ecoli.processes.polypeptide_elongation import PolypeptideElongation
from models.ecoli.processes.transcript_initiation import TranscriptInitiation
from models.ecoli.processes.transcript_elongation import TranscriptElongation
from models.ecoli.processes.protein_degradation import ProteinDegradation
from models.ecoli.processes.equilibrium import Equilibrium
from models.ecoli.processes.tf_binding import TfBinding
from models.ecoli.processes.tf_unbinding import TfUnbinding
from models.ecoli.processes.two_component_system import TwoComponentSystem

# Listeners
from models.ecoli.listeners.mass import Mass
from models.ecoli.listeners.replication_data import ReplicationData
from models.ecoli.listeners.ribosome_data import RibosomeData
from models.ecoli.listeners.unique_molecule_counts import UniqueMoleculeCounts
from models.ecoli.listeners.fba_results import FBAResults
from models.ecoli.listeners.rna_degradation_listener import RnaDegradationListener
from models.ecoli.listeners.transcript_elongation_listener import TranscriptElongationListener
from models.ecoli.listeners.rnap_data import RnapData
from models.ecoli.listeners.enzyme_kinetics import EnzymeKinetics
from models.ecoli.listeners.growth_limits import GrowthLimits
from models.ecoli.listeners.rna_synth_prob import RnaSynthProb
from models.ecoli.listeners.monomer_counts import MonomerCounts
from models.ecoli.listeners.RNA_counts import RNACounts
from models.ecoli.listeners.complexation_listener import ComplexationListener
from models.ecoli.listeners.equilibrium_listener import EquilibriumListener
from models.ecoli.listeners.dna_supercoiling import DnaSupercoiling
from models.ecoli.listeners.rna_maturation_listener import RnaMaturationListener

from models.ecoli.sim.initial_conditions import calcInitialConditions
from wholecell.sim.divide_cell import divide_cell
from models.ecoli.sim.initial_conditions import setDaughterInitialConditions


class EcoliSimulation(Simulation):
	_internalStateClasses = (
		BulkMolecules,
		UniqueMolecules,
		)

	_externalStateClasses = (
		LocalEnvironment,
		)

	_processClasses = (
		(
			TfUnbinding, # Unbind transcription factors from DNA to allow signaling processes before binding back to DNA.
		),
		# Must run after TfUnbinding and before TfBinding
		(
			Equilibrium, 
			TwoComponentSystem,
			RnaMaturation,	# - Converts unprocessed tRNA/rRNA molecules into mature tRNA/rRNAs
							# - Consolidates the different variants of 23S, 16S, and 5S rRNAs into the single
							# variant that is used for ribosomal subunits
		),
		# Must run before TranscriptInitiation
		(
			TfBinding,	# Bind transcription factors to DNA for transcription regulation
		),
		(
			TranscriptInitiation,
			PolypeptideInitiation,
			ChromosomeReplication,	# Performs initiation, elongation, and termination of active partial chromosomes
									# that replicate the chromosome.
			ProteinDegradation,	# Protein degradation sub-model. Encodes molecular simulation of protein degradation as a Poisson process
			RnaDegradation,	# Submodel for RNA degradation. For more details, see models/ecoli/processes/rna_degradation.py
			Complexation, # Macromolecular complexation sub-model. Encodes molecular simulation of macromolecular complexation
		),
		(
			TranscriptElongation,
			PolypeptideElongation,
		),
		# Must run after TranscriptElongation and PolypeptideElongation
		(
			ChromosomeStructure,	# ChromosomeStructure process
									# - Resolve collisions between molecules and replication forks on the chromosome.
									# - Remove and replicate promoters and motifs that are traversed by replisomes.
									# - Reset the boundaries and linking numbers of chromosomal segments.
		),
		(
			Metabolism,	# Metabolism sub-model. Encodes molecular simulation of microbial metabolism using flux-balance analysis.
		),
		(
			CellDivision,	# - Flags the cell for division when a preset division criterion has been met
		),
	)

	_listenerClasses = (
		Mass,
		ReplicationData,
		RibosomeData,
		UniqueMoleculeCounts,
		FBAResults,
		RnaDegradationListener,
		TranscriptElongationListener,
		RnapData,
		EnzymeKinetics,
		GrowthLimits,
		RnaSynthProb,
		MonomerCounts,
		RNACounts,
		ComplexationListener,
		EquilibriumListener,
		DnaSupercoiling,
		RnaMaturationListener,
		)

	_hookClasses = ()

	_initialConditionsFunction = calcInitialConditions

	_divideCellFunction = divide_cell

	_logToShell = True
	_shellColumnHeaders = (
		"Time (s)",
		"Dry mass (fg)",
		"Dry mass fold change",
		"Protein fold change",
		"RNA fold change",
		"Small mol fold change",
		"Expected fold change"
		)

	_logToDisk = False

class EcoliDaughterSimulation(EcoliSimulation):
	_initialConditionsFunction = setDaughterInitialConditions


def ecoli_simulation(**options):
	"""Instantiate an initial EcoliSimulation or a daughter
	EcoliDaughterSimulation with the given options, depending on whether
	there's a non-None `inheritedStatePath` option.
	"""
	is_daughter = options.get('inheritedStatePath', None) is not None

	# runs each process initialization then each listener
	# then updates states

	return EcoliDaughterSimulation(**options) if is_daughter else EcoliSimulation(**options)
