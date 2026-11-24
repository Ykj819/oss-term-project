#include "ModelSwapVolume.h"
#include "Components/BoxComponent.h"
#include "Engine/SkeletalMesh.h"
#include "UObject/ConstructorHelpers.h"
#include "Oss_TermProjectCharacter.h"
#include "StatsComponent.h"

AModelSwapVolume::AModelSwapVolume()
{
	PrimaryActorTick.bCanEverTick = false;

	Box = CreateDefaultSubobject<UBoxComponent>(TEXT("Box"));
	RootComponent = Box;
	Box->InitBoxExtent(FVector(100.f, 250.f, 150.f));
	Box->SetCollisionEnabled(ECollisionEnabled::QueryOnly);
	Box->SetCollisionResponseToAllChannels(ECR_Ignore);
	Box->SetCollisionResponseToChannel(ECC_Pawn, ECR_Overlap);
	Box->SetGenerateOverlapEvents(true);
	Box->SetHiddenInGame(true);
	Box->ShapeColor = FColor(120, 200, 255);

	static ConstructorHelpers::FObjectFinder<USkeletalMesh> DefaultMesh(TEXT("/Game/Characters/HighQualityKnight/SKM_HQKnight_Manny.SKM_HQKnight_Manny"));
	if (DefaultMesh.Succeeded())
	{
		NewMesh = DefaultMesh.Object;
	}

	Box->OnComponentBeginOverlap.AddDynamic(this, &AModelSwapVolume::OnBoxBeginOverlap);
}

void AModelSwapVolume::OnBoxBeginOverlap(UPrimitiveComponent* OverlappedComponent, AActor* OtherActor, UPrimitiveComponent* OtherComp,
	int32 OtherBodyIndex, bool bFromSweep, const FHitResult& SweepResult)
{
	AOss_TermProjectCharacter* Player = Cast<AOss_TermProjectCharacter>(OtherActor);
	if (!Player || !NewMesh || (Player->GetStats() && Player->GetStats()->IsDead()))
	{
		return;
	}
	// ChangeBodyMesh ignores a mesh the player already has (one way)
	Player->ChangeBodyMesh(NewMesh, bSmoke);
}
