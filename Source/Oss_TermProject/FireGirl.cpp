// FireGirl: NPC sitting on a stool; talk to her (E) to level up with souls. Doesn't move.

#include "FireGirl.h"
#include "Oss_TermProjectCharacter.h"
#include "StatsComponent.h"
#include "Components/CapsuleComponent.h"
#include "Components/StaticMeshComponent.h"
#include "Engine/StaticMesh.h"
#include "UObject/ConstructorHelpers.h"
#include "BossProgressSubsystem.h"
#include "DeathSmoke.h"
#include "Kismet/GameplayStatics.h"

namespace
{
	// same half height as the old standing capsule, so actors already placed in the map keep their feet on the floor
	constexpr float CapsuleRadius = 45.f;
	constexpr float CapsuleHalfHeight = 96.f;
}

AFireGirl::AFireGirl()
{
	PrimaryActorTick.bCanEverTick = false;

	Capsule = CreateDefaultSubobject<UCapsuleComponent>(TEXT("Capsule"));
	RootComponent = Capsule;
	Capsule->InitCapsuleSize(CapsuleRadius, CapsuleHalfHeight);
	Capsule->SetCollisionProfileName(UCollisionProfile::BlockAll_ProfileName);
	Capsule->SetCollisionResponseToChannel(ECC_Camera, ECR_Ignore);

	// Meshes face +Y (like the mannequin): yaw -90 turns them to the actor's forward (+X). Pivot = floor under her hips;
	// her knees reach ~55 cm forward, so shift back 20 cm to centre her + the stool in the capsule.
	const FVector MeshOffset(-20.f, 0.f, -CapsuleHalfHeight);
	const FRotator MeshRotation(0.f, -90.f, 0.f);

	Body = CreateDefaultSubobject<UStaticMeshComponent>(TEXT("Body"));
	Body->SetupAttachment(Capsule);
	Body->SetRelativeLocationAndRotation(MeshOffset, MeshRotation);
	Body->SetCollisionEnabled(ECollisionEnabled::NoCollision);
	static ConstructorHelpers::FObjectFinder<UStaticMesh> GirlMesh(TEXT("/Game/Characters/FireGirl/SM_FireGirl.SM_FireGirl"));
	if (GirlMesh.Succeeded())
	{
		Body->SetStaticMesh(GirlMesh.Object);
	}

	Stool = CreateDefaultSubobject<UStaticMeshComponent>(TEXT("Stool"));
	Stool->SetupAttachment(Capsule);
	Stool->SetRelativeLocationAndRotation(MeshOffset, MeshRotation);
	Stool->SetCollisionEnabled(ECollisionEnabled::NoCollision);
	static ConstructorHelpers::FObjectFinder<UStaticMesh> StoolMesh(TEXT("/Game/Characters/FireGirl/SM_FireGirl_Stool.SM_FireGirl_Stool"));
	if (StoolMesh.Succeeded())
	{
		Stool->SetStaticMesh(StoolMesh.Object);
	}
}

void AFireGirl::BeginPlay()
{
	Super::BeginPlay();

	const UBossProgressSubsystem* Progress = GetWorld()->GetSubsystem<UBossProgressSubsystem>();
	if (Progress && Progress->AreAllBossesDefeated())
	{
		Destroy();
	}
}

void AFireGirl::Vanish()
{
	if (IsHidden())
	{
		return;
	}
	// close the level-up menu if it is open with her
	if (AOss_TermProjectCharacter* Player = Cast<AOss_TermProjectCharacter>(UGameplayStatics::GetPlayerPawn(this, 0)))
	{
		if (Player->IsInLevelUpMenu())
		{
			Player->CloseLevelUpMenu();
		}
	}
	Capsule->SetCollisionEnabled(ECollisionEnabled::NoCollision);
	ADeathSmoke::Poof(this);	// hides her at once, smoke covers the body
	SetLifeSpan(3.f);
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
