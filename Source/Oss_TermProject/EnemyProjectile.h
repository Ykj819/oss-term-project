// Thrown rock: flies in an arc, hurts the player once (blockable, rolls pass through), breaks on walls/ground

#pragma once

#include "CoreMinimal.h"
#include "GameFramework/Actor.h"
#include "EnemyProjectile.generated.h"

class UStaticMeshComponent;

UCLASS()
class AEnemyProjectile : public AActor
{
	GENERATED_BODY()

	UPROPERTY(VisibleAnywhere, Category="Components")
	UStaticMeshComponent* Mesh;

public:

	AEnemyProjectile();

	virtual void Tick(float DeltaSeconds) override;

	/** Starts the flight (call right after spawning; the owner is the thrower) */
	void Launch(const FVector& InVelocity, float InGravityZ, float InDamage);

	/** Collision / look radius */
	UPROPERTY(EditAnywhere, Category="Projectile", meta = (ClampMin = 1, Units = "cm"))
	float Radius = 9.f;

	/** Removed after this long if it never hits anything */
	UPROPERTY(EditAnywhere, Category="Projectile", meta = (ClampMin = 0.1, Units = "s"))
	float MaxLifeTime = 5.f;

protected:

	virtual void BeginPlay() override;

	FVector Velocity = FVector::ZeroVector;
	float GravityZ = -490.f;
	float Damage = 15.f;
	float Age = 0.f;
	bool bLaunched = false;

	/** Actors the rock flies through (thrower, other enemies, a rolling player) */
	TArray<TWeakObjectPtr<AActor>> PassThrough;

	FRotator Spin;

	void Break();
};
