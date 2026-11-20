#include "DeathVolume.h"

#include "Components/BoxComponent.h"
#include "Kismet/GameplayStatics.h"
#include "GameFramework/DamageType.h"
#include "Oss_TermProjectCharacter.h"
#include "StatsComponent.h"

ADeathVolume::ADeathVolume()
{
	PrimaryActorTick.bCanEverTick = false;

	Box = CreateDefaultSubobject<UBoxComponent>(TEXT("Box"));
	RootComponent = Box;
	Box->SetBoxExtent(FVector(200.f, 200.f, 100.f));
	Box->SetCollisionProfileName(TEXT("OverlapAllDynamic"));
	Box->SetGenerateOverlapEvents(true);
	Box->ShapeColor = FColor::Red;
	Box->SetHiddenInGame(true);
	Box->OnComponentBeginOverlap.AddDynamic(this, &ADeathVolume::OnBoxOverlap);
}

void ADeathVolume::OnBoxOverlap(UPrimitiveComponent* OverlappedComp, AActor* OtherActor, UPrimitiveComponent* OtherComp,
	int32 OtherBodyIndex, bool bFromSweep, const FHitResult& SweepResult)
{
	if (!OtherActor || OtherActor == this)
	{
		return;
	}

	if (AOss_TermProjectCharacter* Player = Cast<AOss_TermProjectCharacter>(OtherActor))
	{
		if (UStatsComponent* Stats = Player->GetStats())
		{
			if (!Stats->IsDead())
			{
				Stats->ApplyDamage(1.0e9f, this);
			}
		}
		return;
	}

	if (bKillEnemies && OtherActor->IsA<APawn>())
	{
		UGameplayStatics::ApplyDamage(OtherActor, 1.0e9f, nullptr, this, UDamageType::StaticClass());
	}
}
