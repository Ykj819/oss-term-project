// FireGirl: standing NPC; talk to her (E) to level up with souls. Doesn't move.

#include "FireGirl.h"
#include "Oss_TermProjectCharacter.h"
#include "StatsComponent.h"
#include "Animation/AnimSequenceBase.h"
#include "Components/CapsuleComponent.h"
#include "Components/SkeletalMeshComponent.h"
#include "Engine/SkeletalMesh.h"
#include "UObject/ConstructorHelpers.h"

AFireGirl::AFireGirl()
{
	PrimaryActorTick.bCanEverTick = false;

	Capsule = CreateDefaultSubobject<UCapsuleComponent>(TEXT("Capsule"));
	RootComponent = Capsule;
	Capsule->InitCapsuleSize(42.f, 96.f);
	Capsule->SetCollisionProfileName(UCollisionProfile::BlockAll_ProfileName);
	Capsule->SetCollisionResponseToChannel(ECC_Camera, ECR_Ignore);

	// placeholder look: the Quinn mannequin
	Mesh = CreateDefaultSubobject<USkeletalMeshComponent>(TEXT("Mesh"));
	Mesh->SetupAttachment(Capsule);
	Mesh->SetRelativeLocationAndRotation(FVector(0.f, 0.f, -96.f), FRotator(0.f, -90.f, 0.f));
	Mesh->SetCollisionEnabled(ECollisionEnabled::NoCollision);
	static ConstructorHelpers::FObjectFinder<USkeletalMesh> QuinnMesh(TEXT("/Game/Characters/Mannequins/Meshes/SKM_Quinn_Simple.SKM_Quinn_Simple"));
	if (QuinnMesh.Succeeded())
	{
		Mesh->SetSkeletalMeshAsset(QuinnMesh.Object);
	}

	IdleAnimation = TSoftObjectPtr<UAnimSequenceBase>(FSoftObjectPath(TEXT("/Game/Characters/Mannequins/Anims/Unarmed/MM_Idle.MM_Idle")));
}

void AFireGirl::BeginPlay()
{
	Super::BeginPlay();

	if (UAnimSequenceBase* Anim = IdleAnimation.LoadSynchronous())
	{
		Mesh->PlayAnimation(Anim, true);
	}
}

bool AFireGirl::CanInteract_Implementation(AActor* Interactor) const
{
	const AOss_TermProjectCharacter* Player = Cast<AOss_TermProjectCharacter>(Interactor);
	return Player && Player->GetStats() && !Player->GetStats()->IsDead() && !Player->IsInLevelUpMenu();
}

void AFireGirl::Interact_Implementation(AActor* Interactor)
{
	if (AOss_TermProjectCharacter* Player = Cast<AOss_TermProjectCharacter>(Interactor))
	{
		Player->OpenLevelUpMenu(this);
	}
}

FText AFireGirl::GetInteractionPrompt_Implementation() const
{
	return NSLOCTEXT("FireGirl", "TalkPrompt", "Talk");
}
