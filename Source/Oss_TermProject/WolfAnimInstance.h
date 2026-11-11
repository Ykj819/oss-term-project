// Parent class for ABP_Wolf: the boss writes where the head should look, the AnimGraph applies it
// (Slot 'DefaultSlot' -> Transform (Modify) Bone on neck_01, Add to Existing, Component Space, Rotation = HeadLookRotation -> Output Pose)

#pragma once

#include "CoreMinimal.h"
#include "Animation/AnimInstance.h"
#include "WolfAnimInstance.generated.h"

UCLASS()
class UWolfAnimInstance : public UAnimInstance
{
	GENERATED_BODY()

public:

	/** Extra neck rotation (component space, added on top of the animation) turning the head toward the player */
	UPROPERTY(BlueprintReadOnly, Category="Look")
	FRotator HeadLookRotation = FRotator::ZeroRotator;
};
